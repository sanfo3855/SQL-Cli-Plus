import getpass
import shelve
import shutil
import sys
import time
import yaml
import subprocess
import os
import re

# TODO 1: gestire il caso in cui vado ad eliminare file da git sotto src/database -> attualmente si spacca tutto
# TODO 2: salvare la password in cache se e solo se la connessione è andata a buon fine -> ora la salva sempre
# TODO 3: gestire la cache della password per ogni possibile configurazione di connessione -> ora è una per qualsiasi configurazione di connessione

# DEFAULT CONFIG
SQLCLWRAPPER_CONFIG_NAME = '.sqlcl-wrapper.config'

# STANDARD MESSAGES
# Default config structure {SQLCLWRAPPER_CONFIG_NAME} file
DEFAULT_CONFIG_STRUCTURE = f'\n    schema: <schema>\n    host: <host>\n    port: <port>\n    service: <service>\n    verbose: <true | false>'
# Error message for missing {SQLCLWRAPPER_CONFIG_NAME} file
ERROR_CONFIG_MISSING = f'  File {SQLCLWRAPPER_CONFIG_NAME} not found in git project root\n  Please run "sqlcl-wrapper config generate" or create the a file with following content in git root directory:' + DEFAULT_CONFIG_STRUCTURE

def get_git_root_folder():
   # 2. get git root folder
   GIT_ROOT_COMMAND = 'git rev-parse --show-toplevel'
   GIT_ROOT = subprocess.run(GIT_ROOT_COMMAND, shell=True, check=True, capture_output=True, text=True).stdout.strip()
   return GIT_ROOT

def config_generate(arguments:str):
   GIT_ROOT = get_git_root_folder()
   # Generate a file {SQLCLWRAPPER_CONFIG_NAME} with the following content
   # schema: <schema from user input>
   # host: <host from user input>
   # port: <port from user input>
   # service: <service from user input>
   # verbose: <true | false from user input>
   print(f'==== config generate ====')
   print(f'  Generating script file {SQLCLWRAPPER_CONFIG_NAME} in git root folder')
   schema   = input('  Please enter the SCHEMA for config: ')
   host     = input('  Please enter the HOST for config: ')
   port     = input('  Please enter the PORT for config: ')
   service  = input('  Please enter the SERVICE for config: ')
   verbose  = input('  Please enter the VERBOSE for config (true | false): ')
   # Create the file {SQLCLWRAPPER_CONFIG_NAME} with the content
   with open(f'{GIT_ROOT}/{SQLCLWRAPPER_CONFIG_NAME}', 'w') as file:
      file.write(f'schema: {schema}\n')
      file.write(f'host: {host}\n')
      file.write(f'port: {port}\n')
      file.write(f'service: {service}\n')
      file.write(f'verbose: {verbose}\n')
   print(f'  File {SQLCLWRAPPER_CONFIG_NAME} generated in git project root')
   sys.exit(0)


def config_show(arguments:str):
   GIT_ROOT = get_git_root_folder()
   # Read the file {SQLCLWRAPPER_CONFIG_NAME} and print the content
   print(f'==== config show ====')
   print(f'  Reading script file {SQLCLWRAPPER_CONFIG_NAME} in git root folder')
   try:
      with open(f'{GIT_ROOT}/{SQLCLWRAPPER_CONFIG_NAME}', 'r') as file:
         config = yaml.safe_load(file)
         print(f'  schema: {config.get("schema")}')
         print(f'  host: {config.get("host")}')
         print(f'  port: {config.get("port")}')
         print(f'  service: {config.get("service")}')
         print(f'  verbose: {config.get("verbose")}')
   except FileNotFoundError:
      print(ERROR_CONFIG_MISSING)
      sys.exit(1)
   sys.exit(0)


def config_edit(arguments:str):
   GIT_ROOT = get_git_root_folder()
   # Edit the file {SQLCLWRAPPER_CONFIG_NAME} changing the values of the key passed in the arguments
   print(f'==== config edit ====')
   if len(arguments.split(' ')) < 4:
      print(f'  Please provide the key and value to change in the config file')
      print(f'  Valid keys: schema, host, port, service, verbose')
      print(f'  Example: sqlcl-wrapper config edit schema FEND')      
      sys.exit(1)
   if arguments.split(' ')[2] not in ['schema', 'host', 'port', 'service', 'verbose']:
      print(f'  Please provide a valid key to change in the config file')
      print(f'  Valid keys: schema, host, port, service, verbose')
      print(f'  Example: sqlcl-wrapper config edit schema FEND')     
      sys.exit(1)
   print(f'  Editing script file {SQLCLWRAPPER_CONFIG_NAME} in git root folder')
   try:
      with open(f'{GIT_ROOT}/{SQLCLWRAPPER_CONFIG_NAME}', 'r') as file:
         config = yaml.safe_load(file)
   except FileNotFoundError:
      print(ERROR_CONFIG_MISSING)
      sys.exit(1)
   # Get the key (third arguments) and value (fourth arguments) from the arguments
   key = arguments.split(' ')[2]
   value = arguments.split(' ')[3]   
   
   # replace value in key on config
   if key in config:
      config[key] = value
      with open(f'{GIT_ROOT}/{SQLCLWRAPPER_CONFIG_NAME}', 'w') as file:
         yaml.dump(config, file)
      print(f'  Config "{key}" changed to "{value}"')
   sys.exit(0)
      
   
def config_commands(arguments:str):   
   if arguments.startswith('config generate'):
      config_generate(arguments)      
   elif arguments.startswith('config show'):
      config_show(arguments)
   elif arguments.startswith('config edit'):
      config_edit(arguments)
   else:
      print(f'  Please provide a valid command for config')
      print(f'  Valid commands: generate, show, edit')
      sys.exit(1)
      


def get_config():
   GIT_ROOT = get_git_root_folder()
   try:
      with open(f'{GIT_ROOT}/{SQLCLWRAPPER_CONFIG_NAME}', 'r') as file:
         config = yaml.safe_load(file)
   except FileNotFoundError:
      print(ERROR_CONFIG_MISSING)
      sys.exit(1)
   return config


def get_password():
   # get script folder path
   script_folder = os.path.dirname(os.path.realpath(__file__))
   # cache location
   cache_location = os.path.join(script_folder,'sqlcl-wrapper.cache')
   # open a cache file to store the password
   try:
      with shelve.open(cache_location) as cache:
         # if the password is not in the cache or the password is older than 15 minutes, ask the user for the password
         if 'password' not in cache or 'password_save_time' not in cache or time.time() - cache['password_save_time'] > 900:        
            cache['password'] = getpass.getpass('Please enter the SCHEMA password: ',)
         else:
            print('Using cached password')
         # update password_save_time
         cache['password_save_time'] = time.time()
         # return password
         return cache['password']
   except Exception as e:
      print(f'Error: {e}')
      sys.exit(1)

def run_sqlcl_command(arguments:str):
   # 1. read the file sql-cl-wrapper.yaml and 
   try:
      with open(f'./{SQLCLWRAPPER_CONFIG_NAME}', 'r') as file:
         config = yaml.safe_load(file)
   except FileNotFoundError:
      print(ERROR_CONFIG_MISSING)   
      sys.exit(1)

   schema = config.get('schema')
   host = config.get('host')
   port = config.get('port')
   service = config.get('service')
   verbose = config.get('verbose')
   print(f'Using schema: {schema} from config file')

   # 2. Request password from user input and hide it
   password = get_password()

   # 3. generate a sqlcl command following this template echo <arguments> | sqlcl <schema>/<password>@<host>:<port>/<service>
   print(f'\n==== Running command: echo {arguments} | sql {schema}/{password}@{host}:{port}/{service}')
   sqlcl_command = f'echo {arguments} | sql {schema}/{password}@{host}:{port}/{service}'

   # 4. run the sqlcl command in a subprocess
   subprocess.run(sqlcl_command, shell=True, check=True)
  

def get_exported_files(arguments:str):
   # 1. Get the GIT_ROOT/src/database folder
   GIT_ROOT = get_git_root_folder()
   database_folder = os.path.join(GIT_ROOT, 'src', 'database')
   
   # 2. Get the list of files from "git status" (new and staged files ) for "GIT_ROOT/src/database" folder
   git_command = f'git -C {GIT_ROOT} status -u --porcelain {database_folder}'
   command_results = subprocess.run(git_command, shell=True, check=True, capture_output=True, text=True)
   exported_files_string = command_results.stdout
   exported_files = exported_files_string.split('\n')
   
   # 3. remove first 3 characters for every file in the list (to remove the status of the file from output)
   exported_files = [re.sub('^...','',file) for file in exported_files]
   
   # 4. remove files containing /fend/ in the path (already moved in src/database/fend folder)
   exported_files = [file for file in exported_files if re.search('fend', file)]
   return exported_files


def check_exported_files(exported_files):
   if len(exported_files)==0:
      print(f'No files exported. Exiting')
      sys.exit(0)

def print_exported_files(exported_files):
   print(f'\n** Exported files:\n - ' + f'\n - '.join(exported_files))

def replace_fenddev_with_fend_in_files(exported_files):
   # 5.3 For every modified_files replace the content matching regex 'FENDDEV.' with the string 'FEND'
   config = get_config()
   GIT_ROOT = get_git_root_folder()
   print(f'\n** Replacing "FENDDEV." with "FEND" in exported DDL')
   for file in exported_files:
      if file:
         file_path = os.path.join(GIT_ROOT, file)
         with open(file_path, 'r') as f:
            content = f.read()
         content = re.sub(r'FENDDEV.', 'FEND', content)
         with open(file_path, 'w') as f:
            f.write(content)
         if config.get('verbose'):
            print(f'   Replaced content in {file}')

def move_files_to_fend(exported_files):
   config = get_config()
   GIT_ROOT = get_git_root_folder()
   print(f'\n** Moving from src/database/fenddev* to src/database/fend')
   for file in exported_files:
      if file:
         new_file = re.sub('src/database/fenddev./','src/database/fend/', file)
         shutil.move(f'{GIT_ROOT}/{file}', f'{GIT_ROOT}/{new_file}')
         if config.get('verbose'):
            print(f'   Moved {file} to {new_file}')


def delete_folders_in_database_matching_fenddev():
   config = get_config()
   GIT_ROOT = get_git_root_folder()
   print(f'\n** Deleting folders in src/database/ matching the pattern "/fenddev.*/"')
   for root, dirs, files in os.walk(os.path.join(GIT_ROOT,'src','database')):
      for dir in dirs:
         if re.match('fenddev.', dir):
            shutil.rmtree(os.path.join(root, dir))
            if config.get('verbose'):
               print(f'   Deleted {os.path.join(root, dir)}')



def project_export_move_files_to_fend(arguments:str):
   # 1. Get the list of exported files (new and modified files GIT_ROOT/src/database folder)
   exported_files = get_exported_files(arguments)
   
   # 2. Check if there are exported files. If zero, exit.
   check_exported_files(exported_files)
   
   print(f'\n==== project export - move file to "/src/database/fend" ====')
   # 3. Print the list of exported files
   print_exported_files(exported_files)
   
   # 4. For every modified_files replace the content matching regex 'FENDDEV.' with the string 'FEND'
   replace_fenddev_with_fend_in_files(exported_files)   
   
   # 5. move every modified file and folder replacing '/fenddev.*/ with '/fend/' in the path using os library
   move_files_to_fend(exported_files)
      
   # 6. Delete folders in src/database matching the pattern /fenddev.*/
   delete_folders_in_database_matching_fenddev()
   


def project_commands(arguments:str):
   print(f'==== project commands ====')
   # 1. Run the sqlcl command passed in the arguments
   run_sqlcl_command(arguments)

   # 2. Extra step - project export
   if arguments.startswith('project export'):
      project_export_move_files_to_fend(arguments)


# Standard main of python script
if __name__ == '__main__':
   # 1. read all args from command line and saves them in a single string variable "arguments"
   arguments = ' '.join(sys.argv[1:])
   
   # 1. CONFIG COMMAND
   if arguments.startswith('config'):
      config_commands(arguments)
      
   
   # 2. PROJECT COMMAND
   if arguments.startswith('project'):
      project_commands(arguments)
   
   sys.exit(0)