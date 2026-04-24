# Ruter Chatbot AWS setup

Denne mappen er laget for teamet som får repoet overlevert og skal sette opp miljøet i egen AWS-konto.

## Filer

- [network.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/network.yaml)
- [runtime.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/runtime.yaml)
- [cicd.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/cicd.yaml)
- [network.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/network.parameters.handoff.json)
- [runtime.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/runtime.parameters.handoff.json)
- [cicd.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/cicd.parameters.handoff.json)
- [bootstrap-aws.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/bootstrap-aws.yml)

`*.handoff.json` er filene som skal brukes ved overlevering. `*.example.json` er bare referanser.

## Hva må fylles ut

### `network.parameters.handoff.json`

Denne kan normalt brukes som den er. Endre bare hvis dere vil bruke andre CIDR-er enn default.

### `runtime.parameters.handoff.json`

Dere må fylle ut:

- `ConfluenceEmail`
- enten `ConfluenceToken` eller `ConfluenceTokenSecretArn`

`ApiImageUri` og `ChainlitImageUri` kan stå tomme. Hvis de står tomme, utleder `runtime.yaml` automatisk:

- `${account}.dkr.ecr.${region}.amazonaws.com/ruter-chatbot:prod-latest`
- `${account}.dkr.ecr.${region}.amazonaws.com/ruter-chainlit:prod-latest`

### `cicd.parameters.handoff.json`

Det viktigste her er:

- `GitHubRepository`

## Manual bootstrap commands

Dette er hovedsporet for oppstart av et nytt miljø.

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
- eventuelt `infra/cloudformation/network.parameters.handoff.json`

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

## Bootstrap via GitHub Actions

Hvis dere heller vil kjøre init fra GitHub Actions, kan dere bruke [bootstrap-aws.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/bootstrap-aws.yml).

Da må disse repo-secretsene være satt:

- `AWS_BOOTSTRAP_ACCESS_KEY_ID`
- `AWS_BOOTSTRAP_SECRET_ACCESS_KEY`
- `AWS_BOOTSTRAP_SESSION_TOKEN`

Vanlige deploy-workflows bruker fortsatt OIDC etterpå.

## Etter bootstrap

Når bootstrap er ferdig, fungerer disse workflowene:

- [deploy-api.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/deploy-api.yml)
- [deploy-chainlit.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/deploy-chainlit.yml)

De kan trigges ved:

- push til `dev`
- eller `workflow_dispatch`
