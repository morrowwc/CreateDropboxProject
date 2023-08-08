from asyncDropboxRequest import DropboxRequest
import asyncio

number = 'Project Number'
name = 'Project Name'
pm_email = 'Project Manager email'
supe_email = 'Superintendant email'

# Dropbox will not let certain characters to be in folder names
charBlacklist = "#%&{}\<>*?/$!'\":@+`|="
for c in name:
    for b in charBlacklist:
        if c == b:
            print(f"Invalid folder name. Use of '{b}'")
            breakpoint

dropbox_request = DropboxRequest()
asyncio.run(dropbox_request.createProject(number, name, pm_email, supe_email))

