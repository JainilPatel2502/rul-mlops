// Everything runs in Docker: the Jenkins agent only needs Docker Desktop (no Python, no pip on the host).
// Lint / train / test / smoke-test run inside the CI image built from Dockerfile.ci;
// the app itself is built and started with docker compose.
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    environment {
        // Jenkins runs as LocalSystem, whose PATH lacks Docker's CLI folder
        PATH                 = "C:\\Program Files\\Docker\\Docker\\resources\\bin;${env.PATH}"
        CI_IMAGE             = 'rul-ci:latest'
        // Separate compose project + ports so CI never collides with a locally running demo stack
        COMPOSE_PROJECT_NAME = 'rul-ci'
        FRONTEND_PORT        = '8181'
        BACKEND_PORT         = '8100'
        PROM_PORT            = '9190'
        GRAFANA_PORT         = '3100'
        // Optional: set to your Docker Hub user to enable the Publish stage
        DOCKERHUB_USER       = ''
    }

    stages {
        stage('Build CI image') {
            steps { bat 'docker build -f Dockerfile.ci -t %CI_IMAGE% .' }
        }

        stage('Lint') {
            steps { bat 'docker run --rm %CI_IMAGE% ruff check backend ml monitoring scripts' }
        }

        stage('Train model') {
            steps {
                bat 'docker rm -f rul-train-%BUILD_NUMBER% || exit 0'
                bat 'docker run --name rul-train-%BUILD_NUMBER% %CI_IMAGE% python ml/train.py --out /tmp/out'
                bat 'docker cp rul-train-%BUILD_NUMBER%:/tmp/out build_artifacts'
                archiveArtifacts artifacts: 'build_artifacts/**', fingerprint: true
            }
            post { always { bat 'docker rm -f rul-train-%BUILD_NUMBER% || exit 0' } }
        }

        stage('Unit tests') {
            steps {
                bat 'docker rm -f rul-test-%BUILD_NUMBER% || exit 0'
                script {
                    try {
                        bat 'docker run --name rul-test-%BUILD_NUMBER% -w /app/backend %CI_IMAGE% python -m pytest -q --junitxml=/tmp/test-results.xml'
                    } finally {
                        bat 'docker cp rul-test-%BUILD_NUMBER%:/tmp/test-results.xml test-results.xml || exit 0'
                        bat 'docker rm -f rul-test-%BUILD_NUMBER% || exit 0'
                    }
                }
            }
            post { always { junit allowEmptyResults: true, testResults: 'test-results.xml' } }
        }

        stage('Build app images') {
            steps { bat 'docker compose build' }
        }

        stage('Integration test') {
            steps {
                bat 'docker compose up -d --wait --wait-timeout 240'
                // Smoke test runs in a container on the compose network and talks to the services by name
                bat 'docker run --rm --network rul-ci_default %CI_IMAGE% python scripts/smoke_test.py frontend:80 prometheus:9090 grafana:3000'
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
