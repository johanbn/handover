# Ruter Chatbot AWS setup

Denne mappen er laget for teamet som får repoet overlevert og skal sette opp miljøet i egen AWS-konto.

## Filer

- [network.yaml](network.yaml)
- [runtime.yaml](runtime.yaml)
- [cicd.yaml](cicd.yaml)
- [network.parameters.handoff.json](network.parameters.handoff.json)
- [runtime.parameters.handoff.json](runtime.parameters.handoff.json)
- [cicd.parameters.handoff.json](cicd.parameters.handoff.json)
- [bootstrap-aws.yml](../../.github/workflows/bootstrap-aws.yml)

`*.handoff.json` er filene som skal brukes ved overlevering. `*.example.json` er bare referanser.

## Hva må fylles ut

### `network.parameters.handoff.json`

Denne kan normalt brukes som den er. Endre bare hvis dere vil bruke andre CIDR-er enn default.

### `runtime.parameters.handoff.json`

Dere må fylle ut:

- `ConfluenceEmail`
- enten `ConfluenceToken` eller `ConfluenceTokenSecretArn`

Ved bootstrap via GitHub Actions kan `ConfluenceToken` stå tom i filen hvis repo-secret `CONFLUENCE_TOKEN` er satt.

`ApiImageUri` og `ChainlitImageUri` kan stå tomme. Hvis de står tomme, utleder `runtime.yaml` automatisk:

- `${account}.dkr.ecr.${region}.amazonaws.com/ruter-chatbot:prod-latest`
- `${account}.dkr.ecr.${region}.amazonaws.com/ruter-chainlit:prod-latest`

### `cicd.parameters.handoff.json`

Det viktigste her er:

- `GitHubRepository`

## Anbefalt: bootstrap via GitHub Actions

Dette er anbefalt oppstartsspor for teamet som får repoet overlevert.

Flyten er:

1. Fyll ut `infra/cloudformation/runtime.parameters.handoff.json`
2. Endre `infra/cloudformation/network.parameters.handoff.json` bare hvis dere vil bruke andre nettverks-CIDR-er enn default
3. Legg inn disse repo-secretsene i GitHub:
   - `AWS_BOOTSTRAP_ACCESS_KEY_ID`
   - `AWS_BOOTSTRAP_SECRET_ACCESS_KEY`
   - `AWS_BOOTSTRAP_SESSION_TOKEN` hvis dere bruker midlertidige credentials
   - `CONFLUENCE_TOKEN` hvis dere ikke bruker `ConfluenceTokenSecretArn`
4. Gå til GitHub-repoet
5. Åpne `Actions`
6. Velg [bootstrap-aws.yml](../../.github/workflows/bootstrap-aws.yml)
7. Klikk `Run workflow`
8. Velg branch
9. Start workflowen i GitHub UI

Når workflowen kjører, gjør den dette:

1. Oppretter nettverket fra `network.yaml`
2. Oppretter runtime foundation fra `runtime.yaml`
3. Bygger og pusher første API- og Chainlit-image til ECR
4. Aktiverer ECS services, ALB, blue/green og autoscaling
5. Oppretter CI/CD-oppsettet fra `cicd.yaml`
6. Setter repo-variablene `AWS_REGION` og `AWS_ROLE_TO_ASSUME`

Etter dette bruker vanlige deploy-workflows OIDC, ikke bootstrap-secrets.

## Alternativ: manuell bootstrap lokalt

Dette er fallback-sporet hvis dere heller vil kjøre oppsettet fra egen maskin.

### 1. Klon repoet

```powershell
git clone https://github.com/<ORG>/<REPO>.git
cd ruter_chatbot
git checkout dev
```

### 2. Verifiser AWS-auth lokalt

Dette kan være via `~/.aws/credentials`, named profile eller SSO.

```powershell
aws sts get-caller-identity
```

### 3. Fyll ut handoff-filene

Fyll ut:

- `infra/cloudformation/runtime.parameters.handoff.json`
- `infra/cloudformation/network.parameters.handoff.json` bare hvis dere vil endre default nettverks-CIDR-er

### 4. Opprett nettverket

```powershell
aws cloudformation create-stack `
  --region eu-west-1 `
  --stack-name ruter-chatbot-network `
  --template-body file://infra/cloudformation/network.yaml `
  --parameters file://infra/cloudformation/network.parameters.handoff.json
```

```powershell
aws cloudformation wait stack-create-complete `
  --region eu-west-1 `
  --stack-name ruter-chatbot-network
```

### 5. Les ut VPC og subnet-verdier

```powershell
$VpcId = aws cloudformation describe-stacks `
  --region eu-west-1 `
  --stack-name ruter-chatbot-network `
  --query "Stacks[0].Outputs[?OutputKey=='VpcId'].OutputValue | [0]" `
  --output text

$AlbSubnetIds = aws cloudformation describe-stacks `
  --region eu-west-1 `
  --stack-name ruter-chatbot-network `
  --query "Stacks[0].Outputs[?OutputKey=='AlbSubnetIds'].OutputValue | [0]" `
  --output text

$ServiceSubnetIds = aws cloudformation describe-stacks `
  --region eu-west-1 `
  --stack-name ruter-chatbot-network `
  --query "Stacks[0].Outputs[?OutputKey=='ServiceSubnetIds'].OutputValue | [0]" `
  --output text
```

### 6. Lag foundation-parameterfil for runtime

Denne varianten oppretter grunnlaget med `0` tasks før første image er pushet.

```powershell
$params = Get-Content infra/cloudformation/runtime.parameters.handoff.json | ConvertFrom-Json

$params = @(
  $params | Where-Object {
    $_.ParameterKey -notin @(
      'VpcId',
      'AlbSubnetIds',
      'ServiceSubnetIds',
      'ApiDesiredCount',
      'ChainlitDesiredCount',
      'ApiMinCapacity',
      'ChainlitMinCapacity'
    )
  }
) + @(
  @{ ParameterKey = 'VpcId'; ParameterValue = $VpcId }
  @{ ParameterKey = 'AlbSubnetIds'; ParameterValue = $AlbSubnetIds }
  @{ ParameterKey = 'ServiceSubnetIds'; ParameterValue = $ServiceSubnetIds }
  @{ ParameterKey = 'ApiDesiredCount'; ParameterValue = '0' }
  @{ ParameterKey = 'ChainlitDesiredCount'; ParameterValue = '0' }
  @{ ParameterKey = 'ApiMinCapacity'; ParameterValue = '0' }
  @{ ParameterKey = 'ChainlitMinCapacity'; ParameterValue = '0' }
)

$params | ConvertTo-Json -Depth 5 | Set-Content infra/cloudformation/runtime.parameters.bootstrap.foundation.json
```

### 7. Opprett runtime foundation

```powershell
aws cloudformation create-stack `
  --region eu-west-1 `
  --stack-name ruter-chatbot-runtime `
  --template-body file://infra/cloudformation/runtime.yaml `
  --parameters file://infra/cloudformation/runtime.parameters.bootstrap.foundation.json `
  --capabilities CAPABILITY_NAMED_IAM
```

```powershell
aws cloudformation wait stack-create-complete `
  --region eu-west-1 `
  --stack-name ruter-chatbot-runtime
```

### 8. Bygg og push første images

```powershell
$AccountId = aws sts get-caller-identity --query Account --output text
$Registry = "$AccountId.dkr.ecr.eu-west-1.amazonaws.com"
$ApiImage = "$Registry/ruter-chatbot:prod-latest"
$ChainlitImage = "$Registry/ruter-chainlit:prod-latest"
```

```powershell
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin $Registry
```

```powershell
docker build -f Dockerfile.prod -t $ApiImage .
docker push $ApiImage

docker build -f Dockerfile.chainlit -t $ChainlitImage .
docker push $ChainlitImage
```

### 9. Lag full runtime-parameterfil

```powershell
$params = Get-Content infra/cloudformation/runtime.parameters.handoff.json | ConvertFrom-Json

$params = @(
  $params | Where-Object {
    $_.ParameterKey -notin @(
      'VpcId',
      'AlbSubnetIds',
      'ServiceSubnetIds'
    )
  }
) + @(
  @{ ParameterKey = 'VpcId'; ParameterValue = $VpcId }
  @{ ParameterKey = 'AlbSubnetIds'; ParameterValue = $AlbSubnetIds }
  @{ ParameterKey = 'ServiceSubnetIds'; ParameterValue = $ServiceSubnetIds }
)

$params | ConvertTo-Json -Depth 5 | Set-Content infra/cloudformation/runtime.parameters.bootstrap.json
```

### 10. Aktiver full runtime

```powershell
aws cloudformation update-stack `
  --region eu-west-1 `
  --stack-name ruter-chatbot-runtime `
  --template-body file://infra/cloudformation/runtime.yaml `
  --parameters file://infra/cloudformation/runtime.parameters.bootstrap.json `
  --capabilities CAPABILITY_NAMED_IAM
```

```powershell
aws cloudformation wait stack-update-complete `
  --region eu-west-1 `
  --stack-name ruter-chatbot-runtime
```

### 11. Les ut rolle-ARN-er fra runtime

```powershell
$TaskExecutionRoleArn = aws cloudformation describe-stacks `
  --region eu-west-1 `
  --stack-name ruter-chatbot-runtime `
  --query "Stacks[0].Outputs[?OutputKey=='TaskExecutionRoleArn'].OutputValue | [0]" `
  --output text

$BedrockTaskRoleArn = aws cloudformation describe-stacks `
  --region eu-west-1 `
  --stack-name ruter-chatbot-runtime `
  --query "Stacks[0].Outputs[?OutputKey=='BedrockTaskRoleArn'].OutputValue | [0]" `
  --output text
```

### 12. Opprett CI/CD-stacken

```powershell
aws cloudformation create-stack `
  --region eu-west-1 `
  --stack-name ruter-chatbot-cicd `
  --template-body file://infra/cloudformation/cicd.yaml `
  --parameters `
    ParameterKey=GitHubRepository,ParameterValue=<ORG>/<REPO> `
    ParameterKey=TaskExecutionRoleArn,ParameterValue=$TaskExecutionRoleArn `
    ParameterKey=BedrockTaskRoleArn,ParameterValue=$BedrockTaskRoleArn `
  --capabilities CAPABILITY_NAMED_IAM
```

```powershell
aws cloudformation wait stack-create-complete `
  --region eu-west-1 `
  --stack-name ruter-chatbot-cicd
```

### 13. Les ut deploy-rollen

```powershell
$DeployRoleArn = aws cloudformation describe-stacks `
  --region eu-west-1 `
  --stack-name ruter-chatbot-cicd `
  --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsDeployRoleArn'].OutputValue | [0]" `
  --output text
```

### 14. Sett GitHub repo-variabler

Hvis `gh` er installert:

```powershell
gh variable set AWS_REGION --body eu-west-1
gh variable set AWS_ROLE_TO_ASSUME --body $DeployRoleArn
```

Ellers kan disse settes i GitHub UI:

- `AWS_REGION=eu-west-1`
- `AWS_ROLE_TO_ASSUME=<DeployRoleArn>`

## Etter bootstrap

Når bootstrap er ferdig, fungerer disse workflowene:

- [deploy-api.yml](../../.github/workflows/deploy-api.yml)
- [deploy-chainlit.yml](../../.github/workflows/deploy-chainlit.yml)

De kan trigges ved:

- push til `dev`
- eller `workflow_dispatch`
