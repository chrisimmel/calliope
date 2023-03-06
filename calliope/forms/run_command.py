import subprocess

from pydantic import BaseModel


class RunCommandFormModel(BaseModel):
    command: str


# Run command action handler
async def run_command_endpoint(request, data: RunCommandFormModel):

    result = subprocess.run(
        data.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return f"Command returned:\n{result.stdout.decode('utf-8')}"
