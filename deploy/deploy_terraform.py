import shutil

import os
import tempfile
import subprocess
import json
import logging

TERRAFORM_BIN_PATH=r'C:\terraform\terraform'

logging.basicConfig(level=logging.INFO)

# 각 csp에 맞는 Terraform 파일 생성
def create_terraform_files(csp, region, credential_data, temp_dir):
    if csp == 'aws':
        main_tf_content = f"""
        provider "aws" {{
          region = "{region}"
          access_key = "{credential_data['access_key']}"
          secret_key = "{credential_data['secret_key']}"
        }}

        resource "aws_instance" "vm" {{
          ami           = data.aws_ami.ubuntu.id
          instance_type = "t2.micro"
          tags = {{
            Name = "aws-{region} VM"
          }}
        }}

        data "aws_ami" "ubuntu" {{
          most_recent = true
          filter {{
            name   = "name"
            values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
          }}
          owners = ["099720109477"]
        }}
        """

    elif csp == 'gcp':
        main_tf_content = f"""
        provider "google" {{
          credentials = "{credential_data['gcp_credentials']}"
          project     = "{credential_data['project_id']}"
          region      = "{region}"
        }}

        resource "google_compute_instance" "vm" {{
          name         = "gcp-{region} VM"
          machine_type = "e2-micro"
          zone         = "{region}-a"

          boot_disk {{
            initialize_params {{
              image = "ubuntu-2004-focal-v20210720"
            }}
          }}

          network_interface {{
            network = "default"
            access_config {{   
              
            }}
          }}

          tags = ["terraform", "gcp"]
        }}
        """

    # 파일 임시 디렉토리에 저장
    with open(os.path.join(temp_dir, 'main.tf'), 'w') as f:
        f.write(main_tf_content)


# Terraform을 통해 해당 csp의 region에 가상머신 배포
def deploy_vm(csp, region, credential_data):
    # 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp()

    try:
        # Terraform 파일 생성
        create_terraform_files(csp, region, credential_data, temp_dir)

        # Terraform 초기화 및 실행
        subprocess.run([TERRAFORM_BIN_PATH, 'init'], cwd=temp_dir, check=True)
        subprocess.run([TERRAFORM_BIN_PATH, 'apply', '-auto-approve'], cwd=temp_dir, check=True)

        result = subprocess.check_output([TERRAFORM_BIN_PATH, 'output', '-json'], cwd=temp_dir, text=True)
        return json.loads(result)

    except Exception as e:
        logging.error(f"{csp}-{region} VM 배포 중 에러 발생: {e}")
        raise

    finally:
        # 임시 디렉토리 삭제
        shutil.rmtree(temp_dir)


def rollback_vm(csp, region, temp_dir):
    try:
        subprocess.run([TERRAFORM_BIN_PATH, 'destroy', '-auto-approve'], cwd=temp_dir, check=True)
        logging.info(f"VM 롤백 완료: {csp}-{region}")
    except subprocess.CalledProcessError as e:
        logging.error(f"롤백 실패: {e}")
