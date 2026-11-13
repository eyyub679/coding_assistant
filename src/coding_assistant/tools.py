import subprocess
from langchain_core.tools import tool
from coding_assistant.schemas import *
from coding_assistant.config import Config

config=Config()

@tool(args_schema=ReadFileSchema)
def read_file(path):
    """Reads an existing file"""
    try:
        with open(path,"r") as file:
            return {
                "status":"success",
                "content":f"Content of the file '{path}':\n{file.read()}"
            }
    except Exception as e:
        return {
            "status":"error",
            "content":f"Error reading file '{path}' {type(e).__name__}: {e}"
        }

# creates/overwrites a file
@tool(args_schema=WriteFileSchema)
def write_file(path,content):
    """Overwrites or creates a new file and write content to it"""
    try:
        with open(path,"w") as file:
            file.write(content)
            return {
                "status":"success",
                "content":f"Wrote content to the file '{path}'"
            }
        
    except Exception as e:
        return {
            "status":"error",
            "content":f"Error writing to file '{path}' {type(e).__name__}: {e}"
        }

# edits a file (replaces old_text with new_one)
@tool(args_schema=EditFileSchema)
def edit_file(path,old_string,new_string):
    """Edits an existing file"""
    try:
        with open(path,"r") as file:
            content=file.read()
        count=content.count(old_string)
        if count==0:
            return {
                "status":"error",
                "content":"Error: old_string not found"
            }
        elif count>1:
            return {
                "status":"error",
                "content":"Error: old_string must appear once"
            }
        new_content=content.replace(old_string,new_string,1) # third parameter controls how many times we replace
        with open(path,"w") as file:
            file.write(new_content)
            return {
                "status":"success",
                "content":f"Edited file '{path}; replaced {old_string} with {new_string}'"
            }
    except Exception as e:
        return {
            "status":"error",
            "content":f"Error editing file '{path}' {type(e).__name__}: {e}"
        }
@tool(args_schema=RunCommandSchema)
def run_command(command,timeout=config.timeout):
    """Runs a bash command"""
    try:
        response=subprocess.run(
            command,
            shell=True, # enables us to give command as a str not list
            capture_output=True, # doesnt return output unless we set this to true
            text=True, # converts byte string to text,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {
            "status":"error",
            "content":f"Error: command timed out after {timeout}s"
        }
    except Exception as e:
        return {
            "status":"error",
            "content":f"Error running command: {type(e).__name__}: {e}"
        }
    output=response.stdout
    if response.returncode!=0: # if there is a problem
        output+=f"\n[exit code: {response.returncode}\nError: {response.stderr}]"
        # even if there is an error some code can be true and there could be output until the error, so concat the strings
    return {
        "status":"success",
        "content":output or "no output"
    }

@tool(args_schema=AppendToFileSchema)
def append_to_file(path,new_content):
    """Appends new content to a file"""
    try:
        with open(path,"a") as file:
            file.write(new_content)
            return {
                    "status":"success",
                    "content":f"Wrote new content to file '{path}'"
            }
    except Exception as e:
        return {
                "status":"error",
                "content":f"Error appending new content to file '{path}': {type(e).__name__}: {e}"
        }




