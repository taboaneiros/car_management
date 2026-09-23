# Car Management - Sistema de Gestão de Veículos

Sistema web para gestão pessoal de veículos, inspirado no Drivvo. Permite controlar abastecimentos, despesas, calcular consumo de combustível e visualizar relatórios.

## 🚗 Funcionalidades (MVP - Fase 1)

- **Autenticação**: Login por email com django-allauth
- **Veículos**: Cadastro de múltiplos veículos por usuário
- **Abastecimentos**: Registro com cálculo automático de consumo (km/l)
- **Despesas**: Controle de gastos com categorias personalizáveis
- **Dashboard**: Resumo mensal, gráficos e indicadores
- **Responsivo**: Interface mobile-first com Bootstrap 5

## 📋 Pré-requisitos

- Python 3.11+
- pip ou uv (gerenciador de pacotes rápido)

## 🚀 Instalação

### 1. Clone e acesse o diretório

```bash
cd car_management
```

### 2. Crie o ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite o .env com suas configurações
```

### 5. Execute as migrações

```bash
python manage.py migrate
```

### 6. Crie um superusuário (opcional)

```bash
python manage.py createsuperuser
```

### 7. Execute o servidor de desenvolvimento

```bash
python manage.py runserver
```

Acesse: http://localhost:8000

## 📁 Estrutura do Projeto

```
car_management/
├── config/                 # Configurações do Django
│   ├── settings/          # Settings em camadas (base/dev/prod)
│   ├── urls.py            # URLs principais
│   └── wsgi.py            # WSGI para produção
├── apps/                   # Apps Django por domínio
│   ├── users/             # Usuários e perfis
│   ├── vehicles/          # Veículos e ownership
│   ├── fuel/              # Abastecimentos e cálculo de consumo
│   ├── expenses/          # Despesas e categorias
│   └── dashboard/         # Dashboard e agregações
├── templates/             # Templates Django
│   ├── base.html          # Template base
│   ├── dashboard/         # Templates do dashboard
│   ├── vehicles/          # Templates de veículos
│   ├── fuel/              # Templates de abastecimentos
│   └── expenses/          # Templates de despesas
├── static/                # Arquivos estáticos
│   └── css/custom.css     # Estilos customizáveis
├── media/                 # Uploads (anexos)
└── manage.py              # Script de gerenciamento
```

## 🔧 Configuração

### Variáveis de Ambiente (.env)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DJANGO_SETTINGS_MODULE` | Módulo de settings | `config.settings.dev` |
| `SECRET_KEY` | Chave secreta Django | *obrigatório* |
| `DEBUG` | Modo debug | `1` |
| `ALLOWED_HOSTS` | Hosts permitidos | `localhost,127.0.0.1` |
| `DATABASE_URL` | URL do banco | SQLite local |
| `EMAIL_HOST` | Servidor SMTP | - |

## 📊 Cálculo de Consumo

O consumo (km/l) é calculado automaticamente entre dois abastecimentos completos (tanque cheio):

1. Registre um abastecimento marcando "Tanque Cheio"
2. No próximo abastecimento completo, o sistema calcula:
   - **Distância**: Odômetro atual - Odômetro anterior
   - **Consumo**: Distância ÷ Litros do abastecimento atual
   - **Custo/km**: Valor total ÷ Distância

## 🎨 Personalização Visual

O arquivo `static/css/custom.css` usa CSS Custom Properties (variáveis) para facilitar a personalização:

```css
:root {
    --cm-primary: #0d6efd;     /* Cor principal */
    --cm-bg-body: #f8f9fa;     /* Fundo da página */
    --cm-radius-lg: 0.5rem;    /* Bordas arredondadas */
}
```

## 🧪 Testes

```bash
pytest
```

## 📈 Roadmap

### Fase 2 - Manutenções e Lembretes
- Serviços preventivos/corretivos
- Lembretes por data e odômetro
- Notificações por email

### Fase 3 - Relatórios Avançados
- Viagens e percursos
- Checklists
- Exportação CSV/Excel
- Comparativos entre veículos

## 📝 Licença

Este projeto está sob a licença MIT.