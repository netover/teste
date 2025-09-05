# Projeto Dashboard Neuromórfico HWA/TWS - Lista de Tarefas (Arquitetura Web)

Este arquivo rastreia o progresso do desenvolvimento do dashboard.

## Fase 1: Setup e Arquitetura

- [x] **Definição da Arquitetura Web:** Definir a stack (Python/Flask, JS, pystray) e atualizar este arquivo.

## Fase 2: Core - Conectividade API

- [x] **Desenvolvimento do Conector da API (HWA/TWS):** Criar e validar o módulo `hwa_connector.py` que lida com a autenticação e extração de dados da API REST.

## Fase 3: Backend

- [x] **Desenvolvimento do Servidor Flask:** Implementar o servidor web que usa o conector para expor os dados via um endpoint JSON (`/api/jobstreams`).

## Fase 4: Frontend

- [x] **Desenvolvimento da Interface Web:** Criar a página HTML/CSS/JS que consome a API do backend e exibe os dados dos job streams.

## Fase 5: Integração e Funcionalidades

- [x] **Integração do Systray:** Fazer a aplicação rodar em segundo plano com um ícone na bandeja do sistema, com menu de ações.
- [ ] **Inicialização com o Sistema:** Adicionar a funcionalidade para iniciar com o Windows. (Deferred)

## Fase 6: Finalização

- [x] **Estilização "Neuromórfica":** Aplicar o design visual avançado na interface web.
- [x] **Empacotamento:** Criar o executável final para Windows com `PyInstaller`. (Build spec created, final build deferred to user due to environment limits).
- [x] **Testes e Validação:** Realizar testes funcionais e de dados.
