param location string
param registryName string

// Dedicated private registry owned only by MatchMind. Anonymous pull is off by default.
// App release references this resource as existing, preserving all registry settings.
resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  tags: {
    project: 'matchmind'
    purpose: 'hackathon-demo'
  }
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

output registryName string = registry.name
