# Ruter Chatbot AWS setup

Denne mappen er laget for teamet som får repoet overlevert og skal sette opp miljøet i egen AWS-konto.

## Dette får dere

- [network.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/network.yaml)
  - oppretter VPC, internet gateway, route table og to public subnets
- [runtime.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/runtime.yaml)
  - oppretter ECR, ECS cluster, ALB, security groups, target groups, task definitions, ECS services og autoscaling
- [cicd.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/cicd.yaml)
  - oppretter GitHub OIDC provider og deploy-rolle for GitHub Actions
- [bootstrap-aws.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/bootstrap-aws.yml)
  - setter opp alt i riktig rekkefølge

## Filer dere skal bruke

- [network.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/network.parameters.handoff.json)
- [runtime.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/runtime.parameters.handoff.json)
- [cicd.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/cicd.parameters.handoff.json)

`*.example.json` er bare referanser. For overlevering bruker dere `*.handoff.json`.

## Før dere starter

Hovedantakelsen i denne guiden er at dere kjører bootstrap manuelt fra egen maskin med vanlig AWS-auth, for eksempel via:

- `~/.aws/credentials`
- named profile
- AWS SSO

De credentials dere bruker må ha lov til å opprette CloudFormation-stacks, IAM-roller, ECR, ECS, ALB og GitHub OIDC-relatert IAM-oppsett.

Hvis dere i stedet vil kjøre bootstrap fra GitHub Actions, må dere legge inn disse repo-secretsene:

- `AWS_BOOTSTRAP_ACCESS_KEY_ID`
- `AWS_BOOTSTRAP_SECRET_ACCESS_KEY`
- `AWS_BOOTSTRAP_SESSION_TOKEN`

`AWS_BOOTSTRAP_SESSION_TOKEN` trengs bare hvis dere bruker midlertidige credentials.

## Hva dere må fylle ut

### 1. `network.parameters.handoff.json`

Denne kan normalt brukes som den er.

Endre bare hvis dere vil bruke andre CIDR-er enn default.

### 2. `runtime.parameters.handoff.json`

Dere må fylle ut:

- `ConfluenceEmail`
- enten `ConfluenceToken` eller `ConfluenceTokenSecretArn`
- `ApiImageUri`
- `ChainlitImageUri`

Anbefalt:

- bruk `ConfluenceToken` hvis dere vil komme raskt i gang
- bruk `ConfluenceTokenSecretArn` hvis dere allerede bruker Secrets Manager eller SSM

`ApiImageUri` og `ChainlitImageUri` skal peke til ECR-repoene i deres konto, for eksempel:

```json
{
  "ParameterKey": "ApiImageUri",
  "ParameterValue": "123456789012.dkr.ecr.eu-west-1.amazonaws.com/ruter-chatbot:prod-latest"
}
```

```json
{
  "ParameterKey": "ChainlitImageUri",
  "ParameterValue": "123456789012.dkr.ecr.eu-west-1.amazonaws.com/ruter-chainlit:prod-latest"
}
```

### 3. `cicd.parameters.handoff.json`

Denne er mest referanse.

Bootstrap-workflowen leser rolle-ARN-er fra runtime-stacken automatisk, så i praksis er det viktigste her:

- `GitHubRepository`

Hvis repoet hos dere heter noe annet enn originalen, må dere endre dette.

## Anbefalt oppsett

Det finnes to måter å starte opp miljøet på:

### Alternativ A: Manuell bootstrap fra egen maskin

Dette er anbefalt hvis dere allerede bruker `~/.aws/credentials`, profile eller SSO.

Kjør stackene i denne rekkefølgen:

1. `network.yaml`
2. `runtime.yaml`
3. bygg og push første API- og Chainlit-image til ECR
4. oppdater `runtime.yaml` hvis image-tagene ble endret
5. `cicd.yaml`
6. sett GitHub repo-variablene:
   - `AWS_REGION`
   - `AWS_ROLE_TO_ASSUME`

### Alternativ B: Bootstrap via GitHub Actions

Kjør [Bootstrap AWS environment](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/bootstrap-aws.yml) fra GitHub Actions.

Workflowen gjør dette:

1. deployer `network.yaml`
2. henter VPC- og subnet-verdier fra network-stacken
3. deployer `runtime.yaml` i foundation-modus
4. bygger og pusher første API- og Chainlit-image
5. oppdaterer `runtime.yaml` til full service-konfig
6. deployer `cicd.yaml`
7. setter repo-variablene:
   - `AWS_REGION`
   - `AWS_ROLE_TO_ASSUME`

Etter dette kan vanlige deploy-workflows brukes.

## Etter bootstrap

Når bootstrap er ferdig, fungerer disse workflowene:

- [deploy-api.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/deploy-api.yml)
- [deploy-chainlit.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/deploy-chainlit.yml)

De kan trigges ved:

- push til `dev`
- eller `workflow_dispatch`

## Viktige praktiske noter

- `runtime.yaml` bruker ECS-native blue/green
- test listeners på `9001` og `9002` er derfor en del av løsningen
- `runtime.yaml` støtter både secret ARN og vanlig `NoEcho`-parameter for `CONFLUENCE_TOKEN`
- bootstrap lager ikke GitHub-repoet; det forutsetter at repoet allerede finnes

## Kort oppsummering

For mottakerteamet er den praktiske flyten:

1. få repoet
2. fyll ut `runtime.parameters.handoff.json`
3. juster `network.parameters.handoff.json` bare hvis ønskelig
4. bootstrap miljøet enten lokalt eller via GitHub Actions
5. bruk vanlige deploy-workflows videre
