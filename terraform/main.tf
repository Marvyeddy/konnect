data "aws_ssm_parameter" "amazon_linux" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# The Elastic IP is created once outside Terraform and then reused.
data "aws_eip" "konnect" {
  public_ip = var.elastic_ip
}

resource "aws_key_pair" "konnect" {
  key_name   = "${var.project_name}-key"
  public_key = file(var.ssh_public_key_path)
}

resource "aws_security_group" "konnect" {
  name        = "${var.project_name}-sg"
  description = "Security group for Konnect"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    protocol    = "tcp"
    from_port   = 22
    to_port     = 22
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  ingress {
    description = "FastAPI"
    protocol    = "tcp"
    from_port   = 8000
    to_port     = 8000
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "konnect" {
  ami           = data.aws_ssm_parameter.amazon_linux.value
  instance_type = var.instance_type
  subnet_id     = data.aws_subnets.default.ids[0]

  key_name = aws_key_pair.konnect.key_name

  vpc_security_group_ids = [
    aws_security_group.konnect.id
  ]

  user_data = templatefile(
    "${path.module}/user-data.sh",
    {
      docker_image = var.docker_image
    }
  )

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  tags = {
    Name = "${var.project_name}-server"
  }
}

# Attach the existing Elastic IP to the new EC2 instance.
resource "aws_eip_association" "konnect" {
  instance_id   = aws_instance.konnect.id
  allocation_id = data.aws_eip.konnect.id
}
