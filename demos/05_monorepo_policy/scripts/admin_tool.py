"""Internal admin deployment script."""
import subprocess

def deploy_service(service_name: str):
    # CG-SEC-005: Shell execution is disabled for scripts/** via [[codeguard.overrides]]
    subprocess.run(f"systemctl restart {service_name}", shell=True)
