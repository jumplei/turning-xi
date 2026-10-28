targetScope = 'subscription'

param location string = 'eastus2'
param resourceGroupName string = 'rg-matchmind-eastus2'
@description('Bootstrap only the private image registry before remote image build.')
param registryOnly bool = true
param imageTag string = 'pending-build'
param modelEndpoint string = ''
param modelDeployment string = 'gpt-6-luna'
param persistentLogs bool = false
param protectModelAccess bool = false
@minValue(1)
param modelCallLimit int = 800
param modelCallsUsed int = 0
@secure()
param modelKey string = ''
@secure()
param demoAccessToken string = ''

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: resourceGroupName
  location: location
  tags: {
    project: 'matchmind'
    purpose: 'hackathon-demo'
  }
}

var registryName = 'crmm${uniqueString(subscription().subscriptionId, 'matchmind')}'

module bootstrap './registry.bicep' = if (registryOnly) {
  name: 'matchmind-registry'
  scope: rg
  params: {
    location: location
    registryName: registryName
  }
}

module platform './platform.bicep' = if (!registryOnly) {
  name: 'matchmind-platform'
  scope: rg
  params: {
    location: location
    registryName: registryName
    registryOnly: registryOnly
    imageTag: imageTag
    modelEndpoint: modelEndpoint
    modelDeployment: modelDeployment
    persistentLogs: persistentLogs
    protectModelAccess: protectModelAccess
    modelCallLimit: modelCallLimit
    modelCallsUsed: modelCallsUsed
    modelKey: modelKey
    demoAccessToken: demoAccessToken
  }
}

output resourceGroup string = rg.name
output registryName string = registryName
output registryServer string = '${registryName}.azurecr.io'
output appName string = registryOnly ? '' : platform!.outputs.appName
output serviceUrl string = registryOnly ? '' : platform!.outputs.serviceUrl
