param location string
param registryName string
param registryOnly bool
param imageTag string
param modelEndpoint string
param modelDeployment string
param persistentLogs bool = false
param protectModelAccess bool = false
param modelCallLimit int = 800
param modelCallsUsed int = 0
@secure()
param modelKey string
@secure()
param demoAccessToken string

var tags = {
  project: 'matchmind'
  purpose: 'hackathon-demo'
}

// The signed-in deployment identity is Contributor, without role-assignment rights.
// Private registry credentials stay in Container Apps secrets. No IAM grants are made.
resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: registryName
}

resource logs 'Microsoft.OperationalInsights/workspaces@2022-10-01' = if (!registryOnly) {
  name: 'log-matchmind-eastus2'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: { dailyQuotaGb: json('0.2') }
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = if (!registryOnly) {
  name: 'cae-matchmind-eastus2'
  location: location
  tags: tags
  properties: {
    workloadProfiles: [
      { name: 'Consumption', workloadProfileType: 'Consumption' }
    ]
    appLogsConfiguration: persistentLogs ? {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs!.properties.customerId
        sharedKey: logs!.listKeys().primarySharedKey
      }
    } : null
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = if (!registryOnly) {
  name: 'ca-matchmind'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: environment!.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8000
        transport: 'auto'
      }
      secrets: concat([
        { name: 'model-key', value: modelKey }
        { name: 'registry-password', value: registryOnly ? '' : registry.listCredentials().passwords[0].value }
      ], protectModelAccess ? [{ name: 'demo-access-token', value: demoAccessToken }] : [])
      registries: [
        {
          server: registry.properties.loginServer
          username: registry.name
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'matchmind'
          image: '${registry.properties.loginServer}/matchmind:${imageTag}'
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: concat([
            { name: 'AZURE_OPENAI_ENDPOINT', value: modelEndpoint }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: modelDeployment }
            { name: 'AZURE_OPENAI_AUTH_MODE', value: 'api_key' }
            { name: 'AZURE_OPENAI_API_KEY', secretRef: 'model-key' }
            { name: 'PHASELENS_SESSION_CALL_LIMIT', value: string(modelCallLimit) }
            { name: 'PHASELENS_SESSION_CALLS_USED', value: string(modelCallsUsed) }
            { name: 'PHASELENS_SESSION_SECONDS', value: '0' }
          ], protectModelAccess ? [{ name: 'MATCHMIND_ACCESS_TOKEN', secretRef: 'demo-access-token' }] : [])
          probes: [
            {
              type: 'Startup'
              httpGet: { path: '/api/health', port: 8000 }
              periodSeconds: 5
              timeoutSeconds: 3
              failureThreshold: 24
            }
            {
              type: 'Liveness'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 30
              timeoutSeconds: 3
            }
            {
              type: 'Readiness'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
        rules: [
          { name: 'http', http: { metadata: { concurrentRequests: '10' } } }
        ]
      }
    }
  }
}

output registryName string = registry.name
output registryServer string = registry.properties.loginServer
output appName string = registryOnly ? '' : app!.name
output serviceUrl string = registryOnly ? '' : 'https://${app!.properties.configuration.ingress.fqdn}'
