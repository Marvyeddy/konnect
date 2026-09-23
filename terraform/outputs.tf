output "instance_id" {
  value = aws_instance.konnect.id
}

output "public_ip" {
  value = data.aws_eip.konnect.public_ip
}

output "api_url" {
  value = "http://${data.aws_eip.konnect.public_ip}:8000"
}

output "docs_url" {
  value = "http://${data.aws_eip.konnect.public_ip}:8000/docs"
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/konnect-ec2 ec2-user@${data.aws_eip.konnect.public_ip}"
}
