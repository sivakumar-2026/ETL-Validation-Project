pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '60'))
  }

  // 15-min DB poll removed. Git push CI is handled by GitHub Actions
  // (.github/workflows/etl-validation.yml). Jenkins keeps Daily RUN only.
  triggers {
    cron('TZ=Asia/Kolkata\n10 8 * * *')
  }

  parameters {
    choice(
      name: 'ALERT_MODE',
      choices: ['AUTO', 'FORCE_EMAIL', 'FAILURES_ONLY'],
      description: 'AUTO = email on CI/Daily/fail. FORCE_EMAIL = always.'
    )
    booleanParam(
      name: 'FORCE_FULL',
      defaultValue: false,
      description: 'Force full validation + email'
    )
    string(
      name: 'ALERT_EMAIL',
      defaultValue: 'sivakumartorur@gmail.com',
      description: 'Alert recipient'
    )
  }

  environment {
    PYTHON = 'python3'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Install deps') {
      steps {
        sh '${PYTHON} -m pip install --user -r requirements.txt'
      }
    }

    stage('Resolve run type') {
      steps {
        script {
          def userCauses = currentBuild.getBuildCauses('hudson.model.Cause$UserIdCause')
          def timerCauses = currentBuild.getBuildCauses('hudson.triggers.TimerTrigger$TimerTriggerCause')
          def isUser = (userCauses != null && !userCauses.isEmpty())
          def isDaily = (timerCauses != null && !timerCauses.isEmpty())

          if (params.FORCE_FULL) {
            env.FORCE_FULL = '1'
          }

          if (isDaily) {
            env.RUN_TYPE = 'Daily RUN'
            env.DAILY_RUN = '1'
          } else if (isUser) {
            env.RUN_TYPE = 'Manual'
          } else {
            // GitHub push / SCM trigger
            env.RUN_TYPE = 'CI Push'
          }
          echo "RUN_TYPE=${env.RUN_TYPE}"
          currentBuild.description = env.RUN_TYPE
        }
      }
    }

    stage('Run ETL validation') {
      steps {
        sh '''
          set +e
          ${PYTHON} jenkins/ci_validate.py
          echo $? > reports/exit_code.txt
          set -e
          echo "RUN_TYPE=$RUN_TYPE"
          ${PYTHON} jenkins/build_email.py
          ${PYTHON} jenkins/build_pdf.py
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: 'reports/*', allowEmptyArchive: true
        }
      }
    }

    stage('Email alert') {
      steps {
        script {
          def exitCode = 1
          if (fileExists('reports/exit_code.txt')) {
            exitCode = readFile('reports/exit_code.txt').trim() as Integer
          }
          def summary = [:]
          if (fileExists('reports/validation_summary.json')) {
            summary = readJSON file: 'reports/validation_summary.json'
          }
          def failed = (summary.totals?.failed ?: 0) as Integer

          def shouldMail = true
          if (params.ALERT_MODE == 'FAILURES_ONLY') {
            shouldMail = (failed > 0 || exitCode != 0)
          }

          if (shouldMail) {
            def smtpSent = sh(script: '${PYTHON} jenkins/send_email.py', returnStatus: true)
            if (smtpSent != 0) {
              def subject = fileExists('reports/email_subject.txt')
                ? readFile('reports/email_subject.txt').trim()
                : "ETL QA Validation Report - ${env.RUN_TYPE}"
              def body = fileExists('reports/email_body.txt')
                ? readFile('reports/email_body.txt')
                : 'See attached PDF.'
              emailext(
                to: "${params.ALERT_EMAIL}",
                subject: subject,
                body: body,
                mimeType: 'text/plain',
                attachmentsPattern: 'reports/validation_report.pdf',
                attachLog: false
              )
            }
          }

          if (exitCode != 0) {
            error("Validation failed with exit code ${exitCode}")
          }
        }
      }
    }
  }
}
