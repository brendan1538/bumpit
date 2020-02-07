#!/usr/bin/env python

import json
import os
import re
from subprocess import check_output, Popen, PIPE, STDOUT

# Gets the directory for this script
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

def main():
  if os.path.exists(os.path.join(__location__, 'config.json')):
    startChecks()
  else:
    print("It looks like this is your first time using BUMPIT.\nLet's set up a configuration for future use.")
    projectRoot = raw_input('Enter path for the project root (beginning with ~/): ')
    willRunAgainstSpecificBranch = raw_input('Only run BUMPIT against a certain branch type (Y/n): ')
    if willRunAgainstSpecificBranch.lower() == 'y' or willRunAgainstSpecificBranch.lower() == 'yes':
      onlyRunOnBranchType = raw_input("Enter the branch type: ")
    else:
      onlyRunOnBranchType = 'any'
    changelogLatestVersionLineNum = raw_input('Line number of the latest version in CHANGELOG.md: ')

    configData = {
      "projectRoot": projectRoot,
      "onlyRunOnBranchType": onlyRunOnBranchType,
      "changelogLatestVersionLineNum": changelogLatestVersionLineNum
    }

    with open(os.path.join(__location__, 'config.json'), 'w') as configFile:
      json.dump(configData, configFile, indent=2, separators=(',', ': '))
    startChecks()

def startChecks():
  # Open and decode config json file
  configJSON = open(os.path.join(__location__, 'config.json'), 'r+').read()
  config = json.loads(configJSON)
  currentBranch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])

  gstOut = check_output(['git', 'status'])

  if (config['onlyRunOnBranchType'] == 'any') or (re.search('^{}'.format(config['onlyRunOnBranchType']), currentBranch)):
    if findSemVerFiles(gstOut):
      print('BUMPIT passed 1')
    else:
      # @TODO: replace master with branch from config (create config with user input first time hook is run)
      glogOut = Popen(['git', 'log', 'origin/master..HEAD'], stdout=PIPE, stderr=STDOUT)
      glogSTDOUT,glogSTDERR = glogOut.communicate()
      if glogSTDERR:
        print(glogSTDERR)
        print('This is not an error with BUMPIT. Please see above git log error to troubleshoot.')
      else:
        hashesToCheck = re.findall('[0-9a-f]{40,40}', glogSTDOUT, re.IGNORECASE)
        if len(hashesToCheck) > 0:
          for i in hashesToCheck:
            diffOut = Popen(['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', str(i)])
            diffSTDOUT,diffSTDERR = diffOut.communicate()
            if diffSTDERR:
              print(diffSTDERR)
              print('This is not an error with BUMPIT. Please see above git diff-tree error to troubleshoot.')
            elif findSemVerFiles(str(diffSTDOUT)):
              print("BUMPIT passed 2")
            else:
              autoBump = raw_input("No version updates have been detected\nWould you like to update now? (Y/N) ")
              bumpVersion(autoBump)
        else:
          print('No previous commit hashes to compare against.')

# Bump the semantic version up based on user input
def bumpVersion(bumpInput):
  if (bumpInput.lower() == 'y') or (bumpInput.lower() == 'yes'):
    # Open and decode config json file
    configJSON = open(os.path.join(__location__, 'config.json'), 'r+').read()
    config = json.loads(configJSON)
    # Store project root from config in rootDir var
    rootDir = os.path.expanduser(config['projectRoot'])

    # Increment version in package.json and add new version to CHANGELOG.md with description
    incrementVersion(config, rootDir)

  elif (bumpInput.lower() == 'n') or (bumpInput.lower() == 'no'):
    print("Opted out of BUMPIT")
  else:
    validInputReq = raw_input('Please enter either Y or N: ')
    bumpVersion(validInputReq)

# Search git output for files typically associated with semantic version update (ie package.json, CHANGELOG.md)
# Returns true if both are found, false is one or none are found.
def findSemVerFiles(output):
  if (re.search('CHANGELOG.md', output, re.IGNORECASE)) and (re.search('package.json', output)):
    return True
  else:
    return False

def incrementVersion(config, rootDir):
  versionInput = raw_input('Would you like to increment the major(mj), minor(mn), or patch(p) version? ')
  versionToIncrement = 3
  if versionInput == 'mj':
    versionToIncrement = 0
  elif versionInput == 'mn':
    versionToIncrement = 1
  elif versionInput == 'p':
    versionToIncrement = 2

  if versionToIncrement < 3:
    with open('{}/package.json'.format(rootDir), 'r+') as packageJSON:
      data = json.loads(packageJSON.read())

    tmpVersion = data['version']
    splitVersion = data['version'].split('.')

    # Convert the version we're updating to an int and increment by 1. then, replace that index in splitVersion with the incremented value, but as a string to be joined later.
    splitVersion[versionToIncrement] = str(int(splitVersion[versionToIncrement]) + 1)
    data['version'] = '.'.join(splitVersion)
    print('Bumped version: {} -> {}'.format(tmpVersion, data['version']))

    with open('{}/package.json'.format(rootDir), 'w+') as packageJSON:
      json.dump(data, packageJSON, indent=2, separators=(',', ': '))
      updateChangelog(config, rootDir, data['version'])
  else:
    print('Invalid input. Please enter either mj, mn, or p')
    incrementVersion(config, rootDir)

def updateChangelog(config, rootDir, newVer):
  changelogDesc = raw_input('Enter a description of the updates included in this version: ')
  changelog = open('{}/CHANGELOG.md'.format(rootDir))
  lines = changelog.readlines()
  changelog.close()

  formattedDesc = "# {}\n{}\n\n".format(newVer, changelogDesc)
  lines.insert((int(config['changelogLatestVersionLineNum']) - 1), formattedDesc)
  newChangelog = open('{}/CHANGELOG.md'.format(rootDir), 'w')
  newChangelog.writelines(lines)
  newChangelog.close()
  print('Updated CHANGELOG.md with new version and description.')

if __name__ == "__main__":
  main()
