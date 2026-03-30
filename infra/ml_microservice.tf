# ── ML Risk Scoring Microservice — Lambda + API Gateway ──────────────────────
#
# Deploys the cyber-risk-ml-training FastAPI app as a Lambda container image
# fronted by an HTTP API Gateway.  Called by the main platform's
# EnrichmentOrchestrator when settings.ml_service_url is set.
#
# Resources:
#   - ECR repository for the container image
#   - IAM role + policy for Lambda execution
#   - Lambda function (container image, VPC-less for external API access)
#   - HTTP API Gateway with /{proxy+} integration
#
# Usage:
#   terraform apply -var="ml_ecr_image_uri=031195399879.dkr.ecr.ca-central-1.amazonaws.com/cyber-risk-ml:latest"
# ─────────────────────────────────────────────────────────────────────────────

variable "ml_ecr_image_uri" {
  description = "ECR image URI for the ML microservice (e.g. 031195399879.dkr.ecr.ca-central-1.amazonaws.com/cyber-risk-ml:latest)"
  type        = string
  default     = ""
}

variable "ml_nvd_api_key" {
  description = "NVD API key for the ML microservice"
  type        = string
  sensitive   = true
  default     = ""
}

# ── ECR Repository ───────────────────────────────────────────────────────────

resource "aws_ecr_repository" "ml_service" {
  name                 = "cyber-risk-ml"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Component = "MLMicroservice"
  }
}

# ── IAM ──────────────────────────────────────────────────────────────────────

resource "aws_iam_role" "ml_lambda" {
  name = "cyber-risk-ml-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ml_lambda_basic" {
  role       = aws_iam_role.ml_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ── Lambda Function ──────────────────────────────────────────────────────────

resource "aws_lambda_function" "ml_service" {
  count = var.ml_ecr_image_uri != "" ? 1 : 0

  function_name = "cyber-risk-ml-service"
  package_type  = "Image"
  image_uri     = var.ml_ecr_image_uri
  role          = aws_iam_role.ml_lambda.arn
  timeout       = 60
  memory_size   = 512

  environment {
    variables = {
      NVD_API_KEY = var.ml_nvd_api_key
    }
  }

  tags = {
    Component = "MLMicroservice"
  }
}

# ── API Gateway (HTTP API) ───────────────────────────────────────────────────

resource "aws_apigatewayv2_api" "ml_api" {
  count         = var.ml_ecr_image_uri != "" ? 1 : 0
  name          = "cyber-risk-ml-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "ml_lambda" {
  count              = var.ml_ecr_image_uri != "" ? 1 : 0
  api_id             = aws_apigatewayv2_api.ml_api[0].id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.ml_service[0].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "ml_default" {
  count     = var.ml_ecr_image_uri != "" ? 1 : 0
  api_id    = aws_apigatewayv2_api.ml_api[0].id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.ml_lambda[0].id}"
}

resource "aws_apigatewayv2_stage" "ml_prod" {
  count       = var.ml_ecr_image_uri != "" ? 1 : 0
  api_id      = aws_apigatewayv2_api.ml_api[0].id
  name        = "prod"
  auto_deploy = true
}

resource "aws_lambda_permission" "ml_apigw" {
  count         = var.ml_ecr_image_uri != "" ? 1 : 0
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ml_service[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.ml_api[0].execution_arn}/*/*"
}

# ── Outputs ──────────────────────────────────────────────────────────────────

output "ml_service_api_url" {
  description = "ML microservice API Gateway URL — set this as ML_SERVICE_URL in the platform .env"
  value       = var.ml_ecr_image_uri != "" ? "${aws_apigatewayv2_stage.ml_prod[0].invoke_url}" : ""
}

output "ml_ecr_repository_url" {
  description = "ECR repository URL for pushing ML service container images"
  value       = aws_ecr_repository.ml_service.repository_url
}
