// Declarative pipeline for a Jenkins agent on Windows with Python 3 and Docker Desktop installed.
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    environment {
        // Separate compose project + ports so CI never collides with a locally running demo stack
        COMPOSE_PROJECT_NAME = 'rul-ci'
        FRONTEND_PORT        = '8181'
        BACKEND_PORT         = '8100'
        PROM_PORT            = '9190'
        GRAFANA_PORT         = '3100'
        // Jenkins runs as LocalSystem, whose PATH lacks per-user installs: point at Python and Docker explicitly
        PATH                 = "C:\Users\jaini\AppData\Local\Programs\Python\Python312;C:\Users\jaini\AppData\Local\Programs\Python\Python312\Scripts;C:\Program Files\Docker\Docker\resources\bin;${env.PATH}"
        // Optional: set to your Docker Hub user to enable the Publish stage
        DOCKERHUB_USER       = ''
    }

    stages {
        stage('Install') {
            steps {
                bat 'python -m venv .venv'
                bat '.venv\\Scripts\\python -m pip install -q -r backend\\requirements-dev.txt ruff'
            }
        }

        stage('Lint') {
            steps { bat '.venv\\Scripts\\ruff check backend ml monitoring scripts' }
        }

        stage('Train model') {
            steps {
                bat '.venv\\Scripts\\python ml\\train.py --out build_artifacts'
                archiveArtifacts artifacts: 'build_artifacts/**', fingerprint: true
            }
        }

        stage('Unit tests') {
            steps {
                dir('backend') {
                    bat '..\\.venv\\Scripts\\python -m pytest -q --junitxml=test-results.xml'
                }
            }
            post { always { junit 'backend/test-results.xml' } }
        }

        stage('Build images') {
            steps { bat 'docker compose build' }
        }

        stage('Integration test') {
            steps {
                bat 'docker compose up -d --wait --wait-timeout 240'
                bat ".venv\\Scripts\\python scripts\\smoke_test.py %FRONTEND_PORT% %PROM_PORT% %GRAFANA_PORT%"
            }
            post {
                failure { bat 'docker compose logs --tail=100' }
                always  { bat 'docker compose down -v' }
            }
        }

        stage('Publish images') {
            when { expression { env.DOCKERHUB_USER?.trim() } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub',
                                                  usernameVariable: 'U', passwordVariable: 'P')]) {
                    bat 'echo %P%| docker login -u %U% --password-stdin'
                    bat 'docker tag rul-backend:local %DOCKERHUB_USER%/rul-backend:%BUILD_NUMBER%'
                    bat 'docker tag rul-frontend:local %DOCKERHUB_USER%/rul-frontend:%BUILD_NUMBER%'
                    bat 'docker push %DOCKERHUB_USER%/rul-backend:%BUILD_NUMBER%'
                    bat 'docker push %DOCKERHUB_USER%/rul-frontend:%BUILD_NUMBER%'
                }
            }
        }
    }

    post {
        always { bat 'docker compose down -v || exit 0' }
    }
}
