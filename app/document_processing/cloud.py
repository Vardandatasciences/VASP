import subprocess
import os
from pathlib import Path
import tempfile

def upload_to_s3_cli(file_path, user_name,bucket_name='vasp-pdf-files', region='us-east-1'):
    """
    Upload a file to S3 using AWS CLI commands through Python
    
    Parameters:
    file_path (str): Path to the file to upload
    bucket_name (str): Name of the S3 bucket
    region (str): AWS region name
    
    Returns:
    bool: True if file was uploaded successfully, False otherwise
    """
    try:
        # Convert file path to Path object for better path handling
        file_path= "app/static/"+file_path
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"Error: File {file_path} not found======================================================")
            return False
            
        # Get the file name from the path
        file_name = f"{user_name}_{file_path.name}"
        
        # Construct the AWS CLI command
        aws_command = [
            'aws', 's3', 'cp',
            str(file_path),
            f's3://{bucket_name}/{file_name}',
            '--region', region
        ]
        
        # Execute the AWS CLI command
        result = subprocess.run(
            aws_command,
            capture_output=True,
            text=True
        )
        
        # Check if the command was successful
        if result.returncode == 0:
            print(f"Successfully uploaded {file_name} to {bucket_name}")
            print(f"Output: {result.stdout}")
            return True
        else:
            print(f"Error uploading file: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def verify_aws_cli():
    """
    Verify that AWS CLI is installed and configured
    
    Returns:
    bool: True if AWS CLI is available and configured, False otherwise
    """
    try:
        # Check if AWS CLI is installed
        version_check = subprocess.run(
            ['aws', '--version'],
            capture_output=True,
            text=True
        )
        
        if version_check.returncode != 0:
            print("AWS CLI is not installed. Please install it first.")
            return False
            
        # Check if AWS CLI is configured
        configure_check = subprocess.run(
            ['aws', 'configure', 'list'],
            capture_output=True,
            text=True
        )
        
        if configure_check.returncode != 0:
            print("AWS CLI is not configured. Please run 'aws configure' first.")
            return False
            
        return True
        
    except FileNotFoundError:
        print("AWS CLI is not installed. Please install it first.")
        return False


def download_file_from_s3(bucket_name, file_name, region='us-east-1'):
    """
    Download a file from S3 to a local temporary directory and return its local path.
    """
    try:
        # Create a temporary file path
        temp_dir = tempfile.gettempdir()
        local_path = Path(temp_dir) / file_name

        # AWS CLI command to download
        aws_command = [
            'aws', 's3', 'cp',
            f's3://{bucket_name}/{file_name}',
            str(local_path),
            '--region', region
        ]

        # Execute the AWS CLI command
        result = subprocess.run(
            aws_command,
            capture_output=True,
            text=True
        )

        # Check if the command succeeded
        if result.returncode == 0:
            print(f"File downloaded successfully to {local_path}")
            return str(local_path)
        else:
            raise Exception(f"Download failed: {result.stderr}")

    except Exception as e:
        raise Exception(f"Error downloading file: {str(e)}")

    finally:
        # Clean up temporary file on exit if necessary
        if 'local_path' in locals() and os.path.exists(local_path):
            try:
                os.remove(local_path)
                print(f"Temporary file {local_path} cleaned up.")
            except Exception as cleanup_error:
                print(f"Error cleaning up file: {cleanup_error}")

def download_from_s3_cli(user_name, file_name, bucket_name='vasp-pdf-files', region='us-east-1'):
    """
    Download a file from S3 using AWS CLI commands
    
    Parameters:
    user_name (str): Username to construct the full file name
    file_name (str): Name of the file to download
    bucket_name (str): Name of the S3 bucket
    region (str): AWS region name
    
    Returns:
    str: Path to the downloaded file, or None if download fails
    """
    try:
        # Create a temporary directory if it doesn't exist
        temp_dir = tempfile.gettempdir()
        
        # Construct the full S3 file name (including username prefix)
        s3_file_name = f"{user_name}_{file_name}"

        print(s3_file_name)
        
        # Create local file path
        local_path = Path(temp_dir) / file_name
        
        # Construct the AWS CLI command
        aws_command = [
            'aws', 's3', 'cp',
            f's3://{bucket_name}/{s3_file_name}',
            str(local_path),
            '--region', region
        ]
        
        # Execute the AWS CLI command
        result = subprocess.run(
            aws_command,
            capture_output=True,
            text=True
        )
        
        # Check if the command was successful
        if result.returncode == 0:
            print(f"Successfully downloaded {s3_file_name}")
            return str(local_path)
        else:
            print(f"Error downloading file: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# # Example usage
# if __name__ == "__main__":
#     # First verify AWS CLI is installed and configured
#     if verify_aws_cli():
#         # Example file upload
#         file_path = "static/uploads/tide_invoice.pdf"
#         upload_to_s3_cli(file_path)
#         bucket_name = 'vasp-pdf-files'  # Replace with your bucket name
#         file_name = 'requirements.txt'  # Replace with your file name

#         try:
#             local_file = download_file_from_s3(bucket_name, file_name)
#             print(f"File downloaded to: {local_file}")
#         except Exception as e:
#             print(f"Error: {e}")

