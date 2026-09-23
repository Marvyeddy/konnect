variable "project_name" {
  description = "Project name"
  type        = string
  default     = "konnect"
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "ssh_public_key_path" {
  description = "SSH public key path"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to SSH"
  type        = string
}

variable "docker_image" {
  description = "Docker image"
  type        = string
}
