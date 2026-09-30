# Car Management - Sistema de Gestão de Veículos

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0+-092E20?style=flat&logo=django&logoColor=white)](https://djangoproject.com)
[![PWA](https://img.shields.io/badge/PWA-Offline--First-5A0FC8?style=flat&logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Sistema completo para gestão de veículos pessoais e frotas leves, com suporte a **Progressive Web App (PWA)**, **funcionamento offline com sincronização automática**, relatórios analíticos avançados e interface adaptativa (Dual-View) otimizada para desktops e smartphones.

---

## 🚀 Principais Módulos e Funcionalidades

### 1. 🚗 Gestão de Veículos & Garagem (`apps.vehicles`)
- Cadastro completo de veículos (marca, modelo, versão, ano, placa, renavam, chassi e hodômetro inicial).
- Upload e gerenciamento de fotos do veículo com preview em tempo real.
- Visão detalhada com histórico cronológico unificado, consumo médio, manutenções e inspeções.

### 2. ⛽ Abastecimentos & Consumo (`apps.fuel`)
- Registro de abastecimento com postos, combustíveis (gasolina, etanol, diesel, GNV, eletricidade) e preços.
- Cálculo automático de consumo médio (**km/l** ou **km/m³**) e **Custo por km (R$/km)**.
- Detecção inteligente de tanque cheio, abastecimentos parciais e cálculo entre abastecimentos consecutivos.
- Algoritmo de detecção de *outliers* para dados discrepantes de odômetro ou consumo.

### 3. 💸 Despesas & Categorias (`apps.expenses`)
- Controle de custos operacionais (IPVA, licenciamento, seguro, lavagem, estacionamento, pedágio, multas).
- Categorias de despesas personalizáveis por usuário ou padrões do sistema.
- Anexo de comprovantes e recibos (fotos/PDF).

### 4. 🔧 Manutenções Preventivas e Corretivas (`apps.maintenance`)
- Registro detalhado de revisões, trocas de óleo, filtros, freios, suspensão e reparos.
- Diferenciação entre manutenção preventiva e corretiva.
- Tipos de serviços customizáveis no menu de Gestão (com intervalos padrão em km e meses).
- Registro de oficina, mecânico, custo total e associação a lembretes pendentes.

### 5. 🔔 Lembretes Inteligentes de Revisão (`apps.reminders`)
- Agendamento por **Data**, **Quilometragem (Odômetro)** ou **Ambos** (o que ocorrer primeiro).
- **Assistente Rápido de Agendamento**: atalhos de 1 toque (+6, +12, +24 meses e +5.000, +10.000, +15.000 km calculados a partir do hodômetro atual do carro).
- Status automáticos: *Pendente*, *Próximo do Vencimento* e *Vencido*.
- Lembretes recorrentes configuráveis com disparo de alertas por e-mail.

### 6. 📋 Checklists & Inspeções Veiculares (`apps.checklists`)
- Modelos de checklists customizáveis divididos por categorias (iluminação, motor, pneus, fluidos, segurança).
- Avaliação ágil de itens (*OK*, *Atenção*, *Problema*, *N/A*) com campo de observações pontuais.
- Avaliação automática do status da inspeção (*Aprovado*, *Pendente* ou *Reprovado*).
- Histórico de vistorias com geração de evidências e relatórios.

### 7. 🗺️ Controle de Viagens (`apps.trips`)
- Registro de percursos corporativos e particulares com odômetro inicial e final.
- Cálculo automático de distância percorrida e reembolso/tarifa por km rodado.
- Associação a motoristas, destinos e fretes.

### 8. 📊 Hub de Relatórios Analíticos (`apps.reports`)
- Painel analítico interativo com filtros por veículo e período com gráficos Chart.js:
  - **Visão Geral**: TCO (Total Cost of Ownership), custo médio por km e distribuição de gastos.
  - **Combustível**: evolução de despesas, preço médio por litro ao longo do tempo e eficiência (km/l).
  - **Despesas**: gráfico de rosca (Donut) por categoria e histórico mensal.
  - **Manutenção**: comparativo de investimento Preventivo vs Corretivo e ranking por tipo de serviço.
- Exportação de dados consolidados em formato CSV e relatórios para impressão/PDF.

### 9. 📥 Importação de Dados do Drivvo (`apps.imports`)
- Migração facilitada de dados legados via arquivos CSV exportados do aplicativo Drivvo.
- Importação automática com tratamento transacional de veículos, abastecimentos, despesas e serviços.

---

## 📱 Experiência Mobile & Offline-First (PWA)

O Car Management foi estruturado sob o conceito de **Progressive Web App (PWA)**, atendendo rigorosamente tanto usuários de computadores quanto usuários em trânsito com smartphones:

- **Padrão Dual-View**:
  - **Desktop (`d-none d-md-block`)**: visualização clássica com tabelas completas, filtros avançados e interações HTMX preservadas.
  - **Mobile (`d-md-none`)**: layout nativo com cartões táteis (`.cm-mobile-card-list`), ênfase visual em valores e ações rápidas no polegar.
- **Barra de Navegação Inferior (Bottom Bar)**: atalhos principais e botão flutuante central (**`+`**) que aciona uma *Bottom Action Sheet* para registro rápido de abastecimentos, despesas, manutenções, lembretes, checklists e viagens.
- **Ergonomia Tátil**: campos com `font-size: 16px` (evita zoom indesejado no iOS Safari), barras de ações fixas (*sticky*) no rodapé e ativação automática de teclado numérico (`inputmode="decimal"` / `inputmode="numeric"`).
- **Modo Offline com IndexedDB (`apps.sync`)**:
  - Permite criar registros mesmo **sem conexão à internet**. Os dados são salvos localmente na fila do navegador (`offline_queue`) com confirmação imediata.
  - Cache de dados de referência (`bootstrap_cache`) para preenchimento de seletores (veículos, categorias, tipos de serviço) sem rede.
- **Sincronização Automática em Segundo Plano (Background Auto-Sync)**:
  - Ao detectar reconexão com a internet, o sistema transmite os lotes pendentes para o servidor (`/api/sync/records/`).
  - O backend reconcilia transacionalmente odômetros, recalcula médias de consumo e conclui lembretes vinculados.
  - Modal interativo na interface permite visualizar a fila offline e forçar sincronizações manuais.

---

## 🌐 Internacionalização (i18n)

A plataforma conta com suporte multilíngue nativo e seletor de idiomas na barra superior:
- 🇧🇷 **Português (Brasil)** - Padrão (`pt-BR`)
- 🇺🇸 **Inglês** (`en`)
- 🇪🇸 **Espanhol** (`es`)

---

## 📁 Estrutura Arquitetural

```
car_management/
├── config/                 # Configurações do projeto Django
│   ├── settings/          # Configuração em camadas (base, dev, prod)
│   ├── urls.py            # Roteamento global (i18n, sync, PWA)
│   └── wsgi.py            # Entrypoint WSGI
├── apps/                   # Módulos desacoplados de domínio
│   ├── users/             # Autenticação, perfis e MFA/TOTP
│   ├── vehicles/          # Veículos, odômetro e garagens
│   ├── fuel/              # Abastecimentos, tipos de combustível e consumo
│   ├── expenses/          # Despesas operacionais e categorias
│   ├── maintenance/       # Manutenções (preventiva/corretiva) e tipos de serviço
│   ├── reminders/         # Lembretes por prazo e odômetro
│   ├── checklists/        # Modelos de vistoria e inspeções veiculares
│   ├── trips/             # Viagens, percursos e controle de km
│   ├── reports/           # Hub de relatórios analíticos e gráficos Chart.js
│   ├── imports/           # Parser e importador de backups do Drivvo
│   ├── sync/              # PWA manifest, service worker e engine offline/sync
│   └── dashboard/         # Visão geral, KPIs e widgets resumidos
├── templates/             # Templates HTML com Bootstrap 5 e Crispy Forms
├── static/                # Arquivos estáticos (CSS, JS, ícones PWA)
│   ├── css/custom.css     # Design system, temas claro/escuro e regras mobile
│   ├── js/offline-db.js   # Abstração de armazenamento local com IndexedDB
│   └── js/offline-manager.js # Gestor de conectividade, PWA e auto-sync
├── media/                 # Armazenamento de uploads (fotos e comprovantes)
└── locale/                # Arquivos de tradução compilados (.po/.mo)
```

---

## ⚙️ Instalação e Execução

### 1. Clonar o repositório e preparar o ambiente

```bash
git clone <url-do-repositorio>
cd car_management

# Criar e ativar o ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou: .venv\Scripts\activate  # Windows
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

Crie um arquivo `.env` baseado no exemplo:

```bash
cp .env.example .env
```

| Variável | Descrição | Padrão |
| :--- | :--- | :--- |
| `DJANGO_SETTINGS_MODULE` | Módulo de configuração ativa | `config.settings.dev` |
| `SECRET_KEY` | Chave criptográfica Django | *obrigatório* |
| `DEBUG` | Modo de depuração | `True` |
| `ALLOWED_HOSTS` | Hosts e domínios autorizados | `localhost,127.0.0.1` |
| `DATABASE_URL` | String de conexão do banco | `sqlite:///db.sqlite3` |
| `EMAIL_BACKEND` | Backend de envio de e-mails | Console em dev / SMTP em prod |

### 4. Aplicar migrações do banco de dados

```bash
python manage.py migrate
```

### 5. Compilar traduções (opcional)

```bash
python manage.py compilemessages
```

### 6. Criar superusuário e iniciar a aplicação

```bash
python manage.py createsuperuser
python manage.py runserver
```

Acesse o portal em: **http://localhost:8000**

---

## 🧪 Suíte de Testes Automatizados

O sistema conta com cobertura de testes unitários e de integração para todos os módulos e cenários de sincronização:

```bash
# Executar todos os testes da aplicação
python manage.py test

# Ou com pytest
pytest
```

---

## 📄 Licença

Este projeto é distribuído sob a licença **MIT**. Consulte o arquivo `LICENSE` para obter mais detalhes.