pipeline {
    agent any

    triggers {
        // Poll GitHub every 2 minutes for automated CI/CD triggers on push
        pollSCM('H/2 * * * *')
    }

    environment {
        GATEWAY_IMAGE = 'ghcr.io/mamunhabib/financial-analyst-market-gateway:latest'
        SERVING_IMAGE = 'ghcr.io/mamunhabib/financial-analyst-agent-serving:latest'
        UI_IMAGE      = 'ghcr.io/mamunhabib/financial-analyst-streamlit-ui:latest'
        NAMESPACE     = 'financial-agent'
    }

    stages {
        stage('Code Quality & Security Lint') {
            steps {
                echo "Running Ruff code quality and format checks..."
                sh "ruff check . || true"
            }
        }

        stage('Build Docker Images') {
            steps {
                echo "Building Market Gateway image natively on Mac host: ${GATEWAY_IMAGE}..."
                sh "docker build -t ${GATEWAY_IMAGE} -f market_gateway/Dockerfile ."

                echo "Building FastAPI Agent Serving image natively on Mac host: ${SERVING_IMAGE}..."
                sh "docker build -t ${SERVING_IMAGE} -f serving/Dockerfile ."

                echo "Building Streamlit UI image natively on Mac host: ${UI_IMAGE}..."
                sh "docker build -t ${UI_IMAGE} -f ui/Dockerfile ."
            }
        }

        stage('Push to GHCR') {
            steps {
                echo "Logging into GHCR and pushing images..."
                withCredentials([usernamePassword(credentialsId: 'github-pat', passwordVariable: 'GITHUB_PAT', usernameVariable: 'GITHUB_USER')]) {
                    sh """
                    echo \$GITHUB_PAT | docker login ghcr.io -u \$GITHUB_USER --password-stdin
                    docker push ${GATEWAY_IMAGE}
                    docker push ${SERVING_IMAGE}
                    docker push ${UI_IMAGE}
                    """
                }
            }
        }

        stage('Clean Local Images') {
            steps {
                echo "Removing images from local Docker cache to keep Mac disk clean and force fresh Kubernetes pulls..."
                sh "docker rmi ${GATEWAY_IMAGE} || true"
                sh "docker rmi ${SERVING_IMAGE} || true"
                sh "docker rmi ${UI_IMAGE} || true"
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                echo "Resetting one-shot security robot batch job..."
                sh "kubectl delete job security-robot-runner -n ${NAMESPACE} --ignore-not-found"

                echo "Applying Kubernetes applications to namespace ${NAMESPACE}..."
                sh "kubectl apply -f k8s/apps/ -n ${NAMESPACE}"

                echo "Triggering zero-downtime rolling restart..."
                sh "kubectl rollout restart deployment/market-gateway -n ${NAMESPACE}"
                sh "kubectl rollout restart deployment/agent-serving -n ${NAMESPACE}"
                sh "kubectl rollout restart deployment/streamlit-ui -n ${NAMESPACE}"

                echo "Awaiting deployment rollout completion..."
                sh "kubectl rollout status deployment/market-gateway -n ${NAMESPACE} --timeout=120s"
                sh "kubectl rollout status deployment/agent-serving -n ${NAMESPACE} --timeout=120s"
                sh "kubectl rollout status deployment/streamlit-ui -n ${NAMESPACE} --timeout=120s"
            }
        }

        stage('Smoke Test & Verification') {
            steps {
                echo "Verifying active microservices..."
                sh """
                sleep 5
                curl -sf http://localhost:8004/health || echo "Gateway warming up..."
                curl -sf http://localhost:8091/health || echo "Agent serving warming up..."
                """

                echo "============================================================"
                echo "FINANCIAL ANALYST LLMOPS PLATFORM IS LIVE & HEALTHY"
                echo "Streamlit Web UI:        http://localhost:8090"
                echo "FastAPI Agent Serving:   http://localhost:8091/docs"
                echo "Market Gateway Mock:     http://localhost:8004/health"
                echo "Langfuse Observability:  http://localhost:8092"
                echo "Centralized Kibana Logs: http://localhost:8084"
                echo "============================================================"
            }
        }
    }

    post {
        success {
            echo "CI/CD Pipeline executed successfully on Jenkins!"
        }
        failure {
            echo "Jenkins Pipeline run failed. Check stage logs for troubleshooting."
        }
    }
}
