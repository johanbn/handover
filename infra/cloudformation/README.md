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
- [deploy-config.json](../../.github/deploy-config.json)

`*.handoff.json` er filene som skal brukes ved overlevering. `*.example.json` er bare referanser.

`.github/deploy-config.json` peker deploy-workflowene til riktig AWS-region og
OIDC deploy-role. Den inneholder ikke secrets. For en ny repo-eier/AWS-konto skal
filen ikke redigeres manuelt; den blir skrevet på nytt av `bootstrap-aws.yml`.

## Hva må fylles ut

### `network.parameters.handoff.json`

Denne kan normalt brukes som den er. Endre bare hvis dere vil bruke andre CIDR-er enn default.

### `runtime.parameters.handoff.json`

Dere må fylle ut:

- `ConfluenceEmail`
- repo-secret `CONFLUENCE_TOKEN` i GitHub

`ConfluenceToken` skal stå tom i parameterfilen. Workflowen setter den fra repo-secret `CONFLUENCE_TOKEN` under bootstrap.

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
3. Gå til `Settings -> Actions -> General -> Workflow permissions` i GitHub-repoet og velg `Read and write permissions`
4. Legg inn disse repo-secretsene i GitHub:
   - `AWS_BOOTSTRAP_ACCESS_KEY_ID`
   - `AWS_BOOTSTRAP_SECRET_ACCESS_KEY`
   - `AWS_BOOTSTRAP_SESSION_TOKEN` hvis dere bruker midlertidige credentials
   - `CONFLUENCE_TOKEN`
5. Gå til GitHub-repoet
6. Åpne `Actions`
7. Velg [bootstrap-aws.yml](../../.github/workflows/bootstrap-aws.yml)
8. Klikk `Run workflow`
9. Velg branch
10. Start workflowen i GitHub UI

Hvis repoet allerede har en `.github/deploy-config.json` fra en tidligere eier
eller testkonto, er det forventet. Bootstrap overskriver den med ny `aws_region`
og ny `aws_role_to_assume` for AWS-kontoen som bootstrap-secretsene peker til.

Når workflowen kjører, gjør den dette:

1. Oppretter nettverket fra `network.yaml`
2. Oppretter runtime foundation fra `runtime.yaml`
3. Bygger og pusher første API- og Chainlit-image til ECR
4. Aktiverer ECS services, ALB, blue/green og autoscaling
5. Oppretter CI/CD-oppsettet fra `cicd.yaml`
6. Skriver `.github/deploy-config.json` med `aws_region` og `aws_role_to_assume`

Etter dette bruker vanlige deploy-workflows OIDC, ikke bootstrap-secrets.

For en ny eier er dette steget det som kobler repoet til deres AWS-konto:
`aws_role_to_assume` blir ARN-en til `GitHubActionsDeployRole` som nettopp ble
opprettet i deres konto. Deploy-workflowene leser denne filen og bruker GitHub
OIDC til å anta rollen uten AWS access keys.

Viktig: `Read and write permissions` trengs fordi bootstrap-workflowen committer
`.github/deploy-config.json` tilbake til repoet. Filen inneholder ikke secrets.
Den peker deploy-workflowene til AWS OIDC-rollen som ble opprettet av `cicd.yaml`.
Dette unngår GitHub Actions variables, siden `GITHUB_TOKEN` ikke alltid får lov til
å skrive repo-variabler selv om workflowen har read/write-permissions.

## Etter bootstrap

Når bootstrap er ferdig, fungerer disse workflowene:

- [deploy-api.yml](../../.github/workflows/deploy-api.yml)
- [deploy-chainlit.yml](../../.github/workflows/deploy-chainlit.yml)

De kan trigges ved:

- push til `dev`
- eller `workflow_dispatch`
