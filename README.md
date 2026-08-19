# Workflow Autônomo GLPI 10.0.5 - API de Validação

Este projeto contém uma API desenvolvida com **FastAPI** para testes de integração, consumo e validação de endpoints do **GLPI 10.0.5**. Ele atua como um backend de orquestração que interage com a API REST do GLPI, além de possuir agentes (como o `IntakeAgent`) para realizar a triagem automática de chamados.

## Tecnologias Utilizadas

- **Python 3**
- **FastAPI** para roteamento e construção da API.
- **Docker & Docker Compose** para orquestração da infraestrutura local (banco de dados, mock GLPI local).
- **pytest** + **respx** para testes automatizados e mock de requisições HTTP.
- Integração via API REST nativa do GLPI.

## Estrutura do Projeto

```
/
├── agents/         # Lógica dos agentes (ex: triagem de tickets)
├── tools/          # Ferramentas e integrações (ex: client GLPI)
├── tests/          # Testes automatizados (pytest)
├── .env.example    # Exemplo de variáveis de ambiente
├── compose.yaml    # Configuração da infraestrutura Docker
├── main.py         # Entrypoint da aplicação FastAPI
└── requirements.txt# Dependências do Python
```

## Configuração do Ambiente

1. Clone o repositório.
2. Instale as dependências locais (recomendado usar um ambiente virtual):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # ou .venv\Scripts\activate no Windows
   pip install -r requirements.txt
   ```
3. Copie o arquivo de exemplo de ambiente e insira as suas chaves e tokens de acesso reais (lembre-se de que o `.env` é ignorado pelo `.gitignore` por segurança):
   ```bash
   cp .env.example .env
   ```

## Subindo a Infraestrutura Local

O projeto conta com um ambiente local orquestrado por Docker, que inclui o PostgreSQL para o workflow e o container do GLPI para testes integrados.

```bash
docker compose up --build -d
```
> O comando acima irá inicializar o banco de dados e baixar/executar a imagem `diouxx/glpi:latest`.

## Como Rodar os Testes

Os testes unitários e de integração (com mock da API) ficam na pasta `tests/`. Eles garantem que as chamadas da API do GLPI (como criação de followups, alteração de status e inicialização de sessão) estão funcionando conforme o esperado.

```bash
pytest tests/ -v
```

## Utilizando a API

Com a aplicação rodando localmente (seja pelo docker ou `uvicorn main:app --reload`), a documentação interativa estará disponível em:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

Lá você poderá testar:
- `/health`: Validação da infraestrutura.
- `/glpi/test-connection`: Testa a conectividade e inicialização de sessão.
- `/glpi/ticket/{ticket_id}`: Consulta dados de chamados.
- `/glpi/ticket/{ticket_id}/intake`: Executa a triagem (Intake Agent) via LangGraph/Agentes baseada no ticket.
