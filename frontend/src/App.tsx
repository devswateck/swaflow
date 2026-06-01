import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  AlertCircle,
  Bell,
  BookOpen,
  Bot,
  BrainCircuit,
  CalendarDays,
  ChartNoAxesCombined,
  CheckCircle2,
  ClipboardCopy,
  CreditCard,
  ExternalLink,
  Gauge,
  GitBranchPlus,
  Inbox,
  Link2,
  LogIn,
  LogOut,
  Mail,
  MessageSquareText,
  Package,
  PanelLeft,
  Plus,
  RefreshCw,
  Save,
  Search,
  Settings,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Pencil,
  Trash2,
  UserRound,
  Warehouse,
  Workflow,
  Moon,
  Sun,
  X,
} from "lucide-react";

import { api, realtimeUrl } from "./lib/api";
import { useAuthStore } from "./lib/auth";

type CurrentUser = {
  id: string;
  company_id: string;
  name: string;
  email: string;
  role: string;
  status: string;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
};

type WhatsAppSetup = {
  callback_url: string;
  verify_token: string | null;
  graph_api_version: string;
  app_secret_configured: boolean;
};

type WhatsAppAccount = {
  id: string;
  company_id: string;
  phone_number_id: string;
  business_account_id: string | null;
  verify_token: string;
  status: string;
};

type WhatsAppAccountTest = {
  ok: boolean;
  phone_number_id: string;
  display_phone_number: string | null;
  verified_name: string | null;
  quality_rating: string | null;
};

type AiAgentResponse = {
  id: string;
  company_id: string;
  name: string;
  system_prompt: string;
  conversation_objective: string;
  conversation_guide: string;
  security_rules: string;
  tone: string | null;
  rules: Record<string, unknown>;
  active: boolean;
  created_at: string;
  updated_at: string;
};

type AiFaqEntry = {
  id: string;
  company_id: string;
  question: string;
  answer: string;
  active: boolean;
  created_at: string;
  updated_at: string;
};

type AiFaqUploadResult = {
  total_read: number;
  created: number;
  updated: number;
};

type ToastState = {
  id: number;
  tone: "success" | "error";
  message: string;
};

type AiClassifyResponse = {
  intent: string;
  confidence: number;
  entities: Record<string, unknown>;
};

type AiInteractiveTemplateOption = {
  id: string;
  title: string;
  description?: string | null;
};

type AiInteractiveTemplate = {
  id: string;
  company_id: string;
  name: string;
  action_key: string;
  template_type: "buttons" | "list";
  body_text: string;
  footer_text: string | null;
  button_text: string | null;
  section_title: string | null;
  options: AiInteractiveTemplateOption[];
  usage_instruction: string;
  trigger_mode: "ai_decides" | "after_capture";
  trigger_fields: string[];
  active: boolean;
  created_at: string;
  updated_at: string;
};

type AiAgentForm = {
  name: string;
  active: boolean;
  systemPrompt: string;
  securityRules: string;
  personality: string;
  tone: string;
  language: string;
  schedule: string;
  welcomeMessage: string;
  businessDescription: string;
  productsServices: string;
  conversationObjective: string;
  conversationGuide: string;
  captureFields: string[];
  funnelSteps: string[];
  handoffRule: string;
  model: string;
  temperature: string;
  maxTokens: string;
  knowledgeSources: string;
};

type CompanyIntegrationResponse = {
  id: string;
  company_id: string;
  type: string;
  config: Record<string, unknown>;
  status: string;
  credentials_configured?: boolean;
  created_at: string;
  updated_at: string;
};

type OutboundWebhookResponse = {
  id: string;
  company_id: string;
  event_type: string;
  target_url: string;
  active: boolean;
  secret_configured?: boolean;
  created_at: string;
  updated_at: string;
};

type IntegrationOption = {
  value: string;
  label: string;
};

type IntegrationField = {
  key: string;
  label: string;
  placeholder?: string;
  options?: IntegrationOption[];
};

type IntegrationDefinition = {
  type: string;
  title: string;
  subtitle: string;
  icon: typeof Bot;
  secretLabel: string;
  extraSecretLabel?: string;
  defaultConfig: Record<string, string>;
  fields: IntegrationField[];
};

type IntegrationFormValue = {
  config: Record<string, string>;
  credentials: string;
  secondaryCredentials: string;
  status: string;
};

type ApiMessage = {
  id: string;
  conversation_id: string;
  external_message_id: string | null;
  sender_type: string;
  content: string | null;
  message_type: string;
  created_at: string;
};

type ApiConversation = {
  id: string;
  contact_id: string;
  contact_name: string | null;
  contact_phone: string;
  status: string;
  assigned_user_id: string | null;
  last_message: string | null;
  last_sender_type: string | null;
  last_message_at: string | null;
  unread_count: number;
  funnel_id: string | null;
  funnel_step_id: string | null;
  funnel_name: string | null;
  funnel_step_name: string | null;
};

type ApiFunnelStep = {
  id: string;
  company_id: string;
  funnel_id: string;
  position: number;
  name: string;
  code: string;
  prompt: string;
  objectives: string[];
  transition_criteria: string;
  status: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

type ApiFunnel = {
  id: string;
  company_id: string;
  name: string;
  description: string | null;
  status: string;
  is_default: boolean;
  steps: ApiFunnelStep[];
  created_at: string;
  updated_at: string;
};

type ApiConversationDetail = ApiConversation & {
  messages: ApiMessage[];
};

type ApiProduct = {
  id: string;
  name: string;
  sku: string | null;
  price: number | string;
  currency: string;
  status: string;
};

type ApiInventory = {
  id: string;
  product_id: string;
  quantity_available: number;
  quantity_reserved: number;
  updated_at: string;
};

type ApiOrder = {
  id: string;
  contact_id: string;
  status: string;
  total: number | string;
  currency: string;
  payment_provider: string | null;
  payment_reference: string | null;
  payment_link: string | null;
  payment_status: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

type PaymentLinkResponse = {
  payment_link: string;
  payment_reference: string;
};

type PageKey =
  | "dashboard"
  | "inbox"
  | "products"
  | "inventory"
  | "orders"
  | "appointments"
  | "funnels"
  | "ai"
  | "whatsapp"
  | "integrations"
  | "settings";

type Conversation = {
  id: string;
  contactId: string;
  name: string;
  phone: string;
  message: string;
  state: string;
  assigned: string;
  lastMessageAt: string | null;
  unreadCount: number;
  funnelId: string | null;
  funnelStepId: string | null;
  funnelName: string | null;
  funnelStepName: string | null;
};

type InboxMessage = {
  id: string;
  side: "left" | "right";
  text: string;
  createdAt: string;
};

type Product = {
  id: string;
  name: string;
  sku: string;
  price: number;
  currency: string;
  status: string;
};

type InventoryItem = {
  productId: string;
  available: number;
  reserved: number;
};

type Order = {
  id: string;
  contact: string;
  total: number;
  currency: string;
  status: string;
  paymentStatus: string;
  paymentProvider: string | null;
  paymentReference: string | null;
  paymentLink: string | null;
  paymentExpiresAt: string | null;
  createdAt: string;
};

type Appointment = {
  id: string;
  contact: string;
  scheduledAt: string;
  status: string;
  owner: string;
};

const navItems: Array<{ key: PageKey; label: string; icon: typeof ChartNoAxesCombined }> = [
  { key: "dashboard", label: "Dashboard", icon: ChartNoAxesCombined },
  { key: "inbox", label: "Inbox", icon: Inbox },
  { key: "products", label: "Productos", icon: Package },
  { key: "inventory", label: "Inventario", icon: Warehouse },
  { key: "orders", label: "Ordenes", icon: ShoppingCart },
  { key: "appointments", label: "Citas", icon: CalendarDays },
  { key: "funnels", label: "Funnels", icon: GitBranchPlus },
  { key: "ai", label: "IA", icon: Bot },
  { key: "whatsapp", label: "WhatsApp", icon: MessageSquareText },
  { key: "integrations", label: "Integraciones", icon: Link2 },
  { key: "settings", label: "Ajustes", icon: Settings },
];

const pageCopy: Record<PageKey, { title: string; subtitle: string }> = {
  dashboard: {
    title: "Dashboard comercial",
    subtitle: "Operacion conversacional del MVP",
  },
  inbox: {
    title: "Inbox",
    subtitle: "Conversaciones de WhatsApp con seguimiento humano e IA",
  },
  products: {
    title: "Productos",
    subtitle: "Catalogo que consulta la IA antes de vender",
  },
  inventory: {
    title: "Inventario",
    subtitle: "Stock disponible y reservado por producto",
  },
  orders: {
    title: "Ordenes",
    subtitle: "Pedidos, links de pago y estados comerciales",
  },
  appointments: {
    title: "Citas",
    subtitle: "Agenda para clientes que aun no compran",
  },
  funnels: {
    title: "Funnels",
    subtitle: "Define embudos por tenant y clasifica conversaciones",
  },
  ai: {
    title: "Configuracion IA",
    subtitle: "Prompt, tono, reglas y clasificador de intencion",
  },
  whatsapp: {
    title: "WhatsApp",
    subtitle: "Cuenta Cloud API, webhook y verificacion",
  },
  integrations: {
    title: "Integraciones",
    subtitle: "n8n, calendario, correo y webhooks salientes",
  },
  settings: {
    title: "Ajustes",
    subtitle: "Tenant, usuarios, roles y entorno operativo",
  },
};

const initialAppointments: Appointment[] = [
  { id: "apt-1", contact: "Diana Perez", scheduledAt: "2026-05-20 14:00", status: "scheduled", owner: "Carolina" },
  { id: "apt-2", contact: "Felipe Torres", scheduledAt: "2026-05-21 10:30", status: "confirmed", owner: "Mateo" },
];

const defaultAiAgentForm: AiAgentForm = {
  name: "Asistente comercial SwaFlow",
  active: true,
  systemPrompt:
    "Eres un asistente comercial de WhatsApp. Responde con claridad, valida productos y stock antes de vender, captura datos clave y pasa a un asesor cuando detectes dudas sensibles, quejas o solicitudes fuera de alcance.",
  securityRules:
    "No inventar precios, no prometer disponibilidad sin consultar stock, no pedir datos bancarios completos y no responder temas fuera del negocio.",
  personality: "cercano, confiable, ejecutivo, claro",
  tone: "comercial y amable",
  language: "espanol",
  schedule: "08:00-18:00",
  welcomeMessage:
    "Hola, soy el asistente de SwaFlow. Estoy aqui para ayudarte con productos, pagos y citas. En que puedo ayudarte hoy?",
  businessDescription:
    "SwaFlow ayuda a empresas a operar ventas por WhatsApp con IA, inventario, agenda, pagos y seguimiento humano.",
  productsServices:
    "Automatizacion comercial por WhatsApp\nInbox para asesores\nAgenda de citas\nLinks de pago\nIntegraciones con n8n, calendario y correo",
  conversationObjective:
    "Calificar leads, resolver preguntas frecuentes, recomendar productos, agendar citas y apoyar el cierre de ventas.",
  conversationGuide:
    "1. Primer contacto:\n" +
    "   Enviar el mensaje de bienvenida y solicitar los datos iniciales definidos.\n\n" +
    "2. Datos iniciales completos:\n" +
    "   Enviar el interactivo menu_principal.\n\n" +
    "3. Seleccion de una opcion:\n" +
    "   Interpretar la opcion como intencion actual, responder con el contexto del negocio y continuar el flujo.\n\n" +
    "4. Productos:\n" +
    "   Consultar catalogo e inventario antes de recomendar. Enviar cards cuando corresponda.",
  captureFields: ["Nombre", "Numero de contacto", "Producto de interes", "Fecha", "Horario"],
  funnelSteps: ["Saludo", "Calificacion", "Recomendacion", "Agendar cita", "Enviar pago"],
  handoffRule:
    "Pasar a humano si hay queja, solicitud legal, datos sensibles, negociacion especial o baja confianza de la IA.",
  model: "gpt-4o-mini",
  temperature: "0.5",
  maxTokens: "500",
  knowledgeSources: "Productos, inventario, ordenes, citas, base de conocimiento y conversaciones del tenant.",
};

function createInteractiveTemplateForm() {
  return {
    name: "Menu principal",
    action_key: "menu_principal",
    template_type: "buttons" as "buttons" | "list",
    body_text: "Selecciona una opcion:",
    footer_text: "",
    button_text: "Ver opciones",
    section_title: "Menu principal",
    usage_instruction: "Enviar despues de capturar los datos iniciales del cliente.",
    trigger_mode: "after_capture" as "ai_decides" | "after_capture",
    trigger_fields: "nombre, email, ciudad",
    option1: "Cursos",
    option2: "Productos",
    option3: "Servicio",
  };
}

const formatMoney = (value: number, currency = "COP") =>
  new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);

function getStoredPage(): PageKey {
  const storedPage = localStorage.getItem("swaflow_active_page");
  return navItems.some((item) => item.key === storedPage) ? (storedPage as PageKey) : "dashboard";
}

type ThemeMode = "light" | "dark";

function getStoredTheme(): ThemeMode {
  const value = localStorage.getItem("swaflow_theme");
  return value === "dark" ? "dark" : "light";
}

function formatPhone(phone: string) {
  return phone.startsWith("+") ? phone : `+${phone}`;
}

const integrationDefinitions: IntegrationDefinition[] = [
  {
    type: "calendar",
    title: "Calendario",
    subtitle: "Citas comerciales y recordatorios",
    icon: CalendarDays,
    secretLabel: "Credencial OAuth o API key",
    defaultConfig: {
      provider: "google_calendar",
      calendar_id: "primary",
      timezone: "America/Bogota",
      event_duration_minutes: "30",
      reminder_minutes: "15",
    },
    fields: [
      {
        key: "provider",
        label: "Proveedor",
        options: [
          { value: "google_calendar", label: "Google Calendar" },
          { value: "outlook_calendar", label: "Outlook Calendar" },
          { value: "calendly", label: "Calendly" },
        ],
      },
      { key: "calendar_id", label: "Calendar ID", placeholder: "primary" },
      { key: "timezone", label: "Zona horaria", placeholder: "America/Bogota" },
      { key: "event_duration_minutes", label: "Duracion cita", placeholder: "30" },
      { key: "reminder_minutes", label: "Recordatorio", placeholder: "15" },
    ],
  },
  {
    type: "email",
    title: "Correo",
    subtitle: "Notificaciones transaccionales",
    icon: Mail,
    secretLabel: "Password SMTP o API key",
    defaultConfig: {
      provider: "smtp",
      from_email: "notificaciones@swateck.com",
      from_name: "SwaFlow",
      reply_to: "comercial@swateck.com",
      smtp_host: "",
      smtp_port: "587",
    },
    fields: [
      {
        key: "provider",
        label: "Proveedor",
        options: [
          { value: "smtp", label: "SMTP" },
          { value: "sendgrid", label: "SendGrid" },
          { value: "resend", label: "Resend" },
          { value: "mailgun", label: "Mailgun" },
        ],
      },
      { key: "from_email", label: "Correo origen", placeholder: "notificaciones@empresa.com" },
      { key: "from_name", label: "Nombre origen", placeholder: "SwaFlow" },
      { key: "reply_to", label: "Responder a", placeholder: "comercial@empresa.com" },
      { key: "smtp_host", label: "Host SMTP", placeholder: "smtp.empresa.com" },
      { key: "smtp_port", label: "Puerto SMTP", placeholder: "587" },
    ],
  },
  {
    type: "payments",
    title: "Pasarela de pago",
    subtitle: "Links de pago y webhooks",
    icon: CreditCard,
    secretLabel: "Llave privada Wompi",
    extraSecretLabel: "Clave de eventos Wompi",
    defaultConfig: {
      provider: "wompi",
      environment: "sandbox",
      currency: "COP",
      public_key: "",
      redirect_url: "",
      payment_link_ttl_minutes: "120",
    },
    fields: [
      {
        key: "provider",
        label: "Proveedor",
        options: [
          { value: "wompi", label: "Wompi" },
          { value: "mercado_pago", label: "Mercado Pago" },
          { value: "stripe", label: "Stripe" },
          { value: "mock", label: "Mock" },
        ],
      },
      {
        key: "environment",
        label: "Entorno",
        options: [
          { value: "sandbox", label: "Sandbox" },
          { value: "production", label: "Produccion" },
        ],
      },
      { key: "currency", label: "Moneda", placeholder: "COP" },
      { key: "public_key", label: "Llave publica", placeholder: "pub_..." },
      { key: "redirect_url", label: "URL retorno", placeholder: "https://swaflow.swateck.com/orders" },
      { key: "payment_link_ttl_minutes", label: "Vigencia link (min)", placeholder: "120" },
    ],
  },
  {
    type: "automation",
    title: "Automatizaciones",
    subtitle: "n8n y servicios auxiliares",
    icon: Link2,
    secretLabel: "Token compartido",
    defaultConfig: {
      provider: "n8n",
      base_url: "",
      environment: "production",
      enabled_events: "message.received,order.paid,appointment.created",
    },
    fields: [
      {
        key: "provider",
        label: "Proveedor",
        options: [
          { value: "n8n", label: "n8n" },
          { value: "zapier", label: "Zapier" },
          { value: "make", label: "Make" },
          { value: "custom", label: "Custom" },
        ],
      },
      { key: "base_url", label: "URL base", placeholder: "https://n8n.swateck.com" },
      {
        key: "environment",
        label: "Entorno",
        options: [
          { value: "production", label: "Produccion" },
          { value: "sandbox", label: "Sandbox" },
        ],
      },
      { key: "enabled_events", label: "Eventos", placeholder: "message.received,order.paid" },
    ],
  },
];

const outboundEventOptions: IntegrationOption[] = [
  { value: "message.received", label: "Mensaje recibido" },
  { value: "message.sent", label: "Mensaje enviado" },
  { value: "message.status", label: "Estado de mensaje" },
  { value: "conversation.read", label: "Conversacion leida" },
  { value: "appointment.created", label: "Cita creada" },
  { value: "appointment.cancelled", label: "Cita cancelada" },
  { value: "order.created", label: "Orden creada" },
  { value: "order.waiting_payment", label: "Orden en pago" },
  { value: "order.paid", label: "Orden pagada" },
  { value: "order.cancelled", label: "Orden cancelada" },
  { value: "*", label: "Todos los eventos" },
];

function createIntegrationForm(definition: IntegrationDefinition): IntegrationFormValue {
  return {
    config: { ...definition.defaultConfig },
    credentials: "",
    secondaryCredentials: "",
    status: "pending",
  };
}

function createIntegrationForms(): Record<string, IntegrationFormValue> {
  return Object.fromEntries(
    integrationDefinitions.map((definition) => [
      definition.type,
      createIntegrationForm(definition),
    ]),
  );
}

function stringifyConfig(config: Record<string, unknown> | null | undefined): Record<string, string> {
  return Object.fromEntries(
    Object.entries(config ?? {}).map(([key, value]) => [key, value == null ? "" : String(value)]),
  );
}

function readString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function readStringArray(value: unknown, fallback: string[]) {
  if (!Array.isArray(value)) {
    return fallback;
  }
  return value.filter((item): item is string => typeof item === "string");
}

function aiFormFromAgent(agent: AiAgentResponse | null): AiAgentForm {
  if (!agent) {
    return { ...defaultAiAgentForm };
  }
  const rules = agent.rules ?? {};
  return {
    name: agent.name,
    active: agent.active,
    systemPrompt: agent.system_prompt,
    conversationObjective:
      agent.conversation_objective || readString(rules.conversation_objective, defaultAiAgentForm.conversationObjective),
    conversationGuide:
      agent.conversation_guide || readString(rules.conversation_guide, defaultAiAgentForm.conversationGuide),
    securityRules: agent.security_rules || readString(rules.guardrails, defaultAiAgentForm.securityRules),
    personality: readString(rules.personality, defaultAiAgentForm.personality),
    tone: agent.tone ?? readString(rules.tone, defaultAiAgentForm.tone),
    language: readString(rules.language, defaultAiAgentForm.language),
    schedule: readString(rules.schedule, defaultAiAgentForm.schedule),
    welcomeMessage: readString(rules.welcome_message, defaultAiAgentForm.welcomeMessage),
    businessDescription: readString(
      rules.business_description,
      defaultAiAgentForm.businessDescription,
    ),
    productsServices: readString(rules.products_services, defaultAiAgentForm.productsServices),
    captureFields: readStringArray(rules.capture_fields, defaultAiAgentForm.captureFields),
    funnelSteps: readStringArray(rules.funnel_steps, defaultAiAgentForm.funnelSteps),
    handoffRule: readString(rules.handoff_rule, defaultAiAgentForm.handoffRule),
    model: readString(rules.model, defaultAiAgentForm.model),
    temperature: readString(rules.temperature, defaultAiAgentForm.temperature),
    maxTokens: readString(rules.max_tokens, defaultAiAgentForm.maxTokens),
    knowledgeSources: readString(rules.knowledge_sources, defaultAiAgentForm.knowledgeSources),
  };
}

function aiPayloadFromForm(form: AiAgentForm) {
  return {
    name: form.name,
    system_prompt: form.systemPrompt,
    conversation_objective: form.conversationObjective,
    conversation_guide: form.conversationGuide,
    security_rules: form.securityRules,
    tone: form.tone,
    active: form.active,
    rules: {
      personality: form.personality,
      tone: form.tone,
      language: form.language,
      schedule: form.schedule,
      welcome_message: form.welcomeMessage,
      business_description: form.businessDescription,
      products_services: form.productsServices,
      capture_fields: form.captureFields,
      funnel_steps: form.funnelSteps,
      handoff_rule: form.handoffRule,
      model: form.model,
      temperature: form.temperature,
      max_tokens: form.maxTokens,
      knowledge_sources: form.knowledgeSources,
      conversation_guide: form.conversationGuide,
    },
  };
}

function aiChecklist(form: AiAgentForm) {
  return [
    { label: "Nombre del agente", done: Boolean(form.name.trim()) },
    { label: "Prompt del sistema", done: form.systemPrompt.trim().length > 40 },
    { label: "Reglas de seguridad", done: form.securityRules.trim().length > 20 },
    { label: "Personalidad y tono", done: Boolean(form.personality.trim() && form.tone.trim()) },
    { label: "Mensaje de bienvenida", done: Boolean(form.welcomeMessage.trim()) },
    { label: "Contexto del negocio", done: form.businessDescription.trim().length > 40 },
    { label: "Productos o servicios", done: form.productsServices.trim().length > 20 },
    { label: "Objetivo de conversacion", done: form.conversationObjective.trim().length > 20 },
    { label: "Guion conversacional", done: form.conversationGuide.trim().length > 40 },
  ];
}

function mapConversationStatus(status: string, lastSenderType: string | null) {
  if (status === "closed") {
    return "Cerrada";
  }
  if (status === "waiting_human") {
    return "Handoff";
  }
  if (lastSenderType === "customer") {
    return "Nuevo";
  }
  return "Abierta";
}

function mapApiConversation(conversation: ApiConversation): Conversation {
  return {
    id: conversation.id,
    contactId: conversation.contact_id,
    name: conversation.contact_name || formatPhone(conversation.contact_phone),
    phone: formatPhone(conversation.contact_phone),
    message: conversation.last_message ?? "Sin mensajes",
    state: mapConversationStatus(conversation.status, conversation.last_sender_type),
    assigned: conversation.assigned_user_id ? "Equipo comercial" : "IA",
    lastMessageAt: conversation.last_message_at,
    unreadCount: conversation.unread_count,
    funnelId: conversation.funnel_id,
    funnelStepId: conversation.funnel_step_id,
    funnelName: conversation.funnel_name,
    funnelStepName: conversation.funnel_step_name,
  };
}

function mapApiMessage(message: ApiMessage): InboxMessage {
  return {
    id: message.id,
    side: message.sender_type === "customer" ? "left" : "right",
    text: message.content ?? `[${message.message_type}]`,
    createdAt: message.created_at,
  };
}

function mapApiProduct(product: ApiProduct): Product {
  const parsedPrice = typeof product.price === "number" ? product.price : Number(product.price);
  return {
    id: product.id,
    name: product.name,
    sku: product.sku ?? "-",
    price: Number.isFinite(parsedPrice) ? parsedPrice : 0,
    currency: product.currency || "COP",
    status: product.status,
  };
}

function mapApiInventory(item: ApiInventory): InventoryItem {
  return {
    productId: item.product_id,
    available: item.quantity_available,
    reserved: item.quantity_reserved,
  };
}

function mapApiOrder(order: ApiOrder): Order {
  const parsedTotal = typeof order.total === "number" ? order.total : Number(order.total);
  const paymentMetadata =
    order.metadata_json.payment && typeof order.metadata_json.payment === "object"
      ? (order.metadata_json.payment as Record<string, unknown>)
      : {};
  const contactName =
    order.metadata_json.contact_name ??
    order.metadata_json.customer_name ??
    `Contacto ${order.contact_id.slice(0, 8)}`;
  return {
    id: order.id,
    contact: String(contactName),
    total: Number.isFinite(parsedTotal) ? parsedTotal : 0,
    currency: order.currency || "COP",
    status: order.status,
    paymentStatus: order.payment_status,
    paymentProvider: order.payment_provider,
    paymentReference: order.payment_reference,
    paymentLink: order.payment_link,
    paymentExpiresAt:
      typeof paymentMetadata.expires_at === "string" ? paymentMetadata.expires_at : null,
    createdAt: order.created_at,
  };
}

function App() {
  const { token, setToken } = useAuthStore();
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [authLoading, setAuthLoading] = useState(Boolean(token));
  const [activePage, setActivePage] = useState<PageKey>(getStoredPage);
  const [theme, setTheme] = useState<ThemeMode>(getStoredTheme);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationMessages, setConversationMessages] = useState<InboxMessage[]>([]);
  const [inboxLoading, setInboxLoading] = useState(false);
  const [inboxError, setInboxError] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [appointments, setAppointments] = useState(initialAppointments);
  const [funnels, setFunnels] = useState<ApiFunnel[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const selectedConversationIdRef = useRef<string | null>(null);

  const page = pageCopy[activePage];
  const selectedConversation = selectedConversationId
    ? conversations.find((item) => item.id === selectedConversationId) ?? null
    : null;
  const totalUnread = useMemo(
    () => conversations.reduce((total, conversation) => total + conversation.unreadCount, 0),
    [conversations],
  );

  useEffect(() => {
    localStorage.setItem("swaflow_active_page", activePage);
  }, [activePage]);

  useEffect(() => {
    localStorage.setItem("swaflow_theme", theme);
    document.documentElement.classList.toggle("theme-dark", theme === "dark");
  }, [theme]);

  useEffect(() => {
    selectedConversationIdRef.current = selectedConversationId;
  }, [selectedConversationId]);

  const loadInbox = useCallback(async ({ showLoading = false }: { showLoading?: boolean } = {}) => {
    if (showLoading) {
      setInboxLoading(true);
    }
    setInboxError("");
    try {
      const response = await api<ApiConversation[]>("/conversations");
      const mapped = response.map(mapApiConversation);
      setConversations(mapped);
      const currentSelected = selectedConversationIdRef.current;
      const nextSelected =
        currentSelected && mapped.some((conversation) => conversation.id === currentSelected)
          ? currentSelected
          : null;
      setSelectedConversationId(nextSelected);
      if (!nextSelected) {
        setConversationMessages([]);
      }
    } catch (caught) {
      setInboxError(caught instanceof Error ? caught.message : "No fue posible actualizar el inbox");
    } finally {
      if (showLoading) {
        setInboxLoading(false);
      }
    }
  }, []);

  const loadConversationDetail = useCallback(async (conversationId: string, markRead = true) => {
    setInboxError("");
    try {
      const detail = await api<ApiConversationDetail>(`/conversations/${conversationId}`);
      setConversationMessages(detail.messages.map(mapApiMessage));
      if (markRead) {
        await api<unknown>(`/conversations/${conversationId}/read`, { method: "POST" }).catch(() => null);
      }
      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === detail.id
            ? { ...mapApiConversation(detail), unreadCount: markRead ? 0 : detail.unread_count }
            : conversation,
        ),
      );
    } catch (caught) {
      setInboxError(caught instanceof Error ? caught.message : "No fue posible cargar la conversacion");
    }
  }, []);

  const loadProducts = useCallback(async () => {
    try {
      const response = await api<ApiProduct[]>("/products?limit=200&offset=0&include_inactive=true");
      setProducts(response.map(mapApiProduct));
    } catch {
      setProducts([]);
    }
  }, []);

  const loadInventory = useCallback(async () => {
    try {
      const response = await api<ApiInventory[]>("/inventory?limit=200&offset=0");
      setInventory(response.map(mapApiInventory));
    } catch {
      setInventory([]);
    }
  }, []);

  const loadCatalogData = useCallback(async () => {
    await Promise.all([loadProducts(), loadInventory()]);
  }, [loadInventory, loadProducts]);

  const loadOrders = useCallback(async () => {
    const response = await api<ApiOrder[]>("/orders?limit=200&offset=0");
    setOrders(response.map(mapApiOrder));
  }, []);

  useEffect(() => {
    if (!token) {
      setCurrentUser(null);
      setAuthLoading(false);
      return;
    }

    let cancelled = false;
    setAuthLoading(true);
    api<CurrentUser>("/auth/me")
      .then((user) => {
        if (!cancelled) {
          setCurrentUser(user);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setToken(null);
          setCurrentUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAuthLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [setToken, token]);

  useEffect(() => {
    if (!currentUser) {
      return;
    }

    void loadInbox({ showLoading: true });
    void loadCatalogData();
    void loadOrders();
  }, [currentUser, loadCatalogData, loadInbox, loadOrders]);

  useEffect(() => {
    if (!currentUser) {
      return;
    }
    api<ApiFunnel[]>("/funnels")
      .then(setFunnels)
      .catch(() => setFunnels([]));
  }, [currentUser]);

  useEffect(() => {
    if (!selectedConversationId) {
      setConversationMessages([]);
      return;
    }

    void loadConversationDetail(selectedConversationId);
  }, [loadConversationDetail, selectedConversationId]);

  useEffect(() => {
    if (!currentUser || !token) {
      return;
    }

    let closed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let pingTimer: number | undefined;

    function connect() {
      socket = new WebSocket(realtimeUrl("/realtime/ws"));
      socket.onopen = () => {
        socket?.send(JSON.stringify({ type: "auth", token }));
        pingTimer = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
          }
        }, 30000);
      };
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as {
          type?: string;
          payload?: { conversation_id?: string };
        };
        if (message.type === "ready" || message.type === "pong") {
          return;
        }
        const conversationId = message.payload?.conversation_id;
        if (conversationId && selectedConversationIdRef.current === conversationId) {
          void loadConversationDetail(conversationId);
          return;
        }
        void loadInbox();
      };
      socket.onclose = (event) => {
        if (pingTimer) {
          window.clearInterval(pingTimer);
        }
        if (event.code === 1008) {
          setToken(null);
          return;
        }
        if (!closed) {
          reconnectTimer = window.setTimeout(connect, 3000);
        }
      };
      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();

    return () => {
      closed = true;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }
      if (pingTimer) {
        window.clearInterval(pingTimer);
      }
      socket?.close();
    };
  }, [currentUser, loadConversationDetail, loadInbox, setToken, token]);

  const filteredProducts = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (activePage !== "products" || !value) {
      return products;
    }
    return products.filter(
      (product) =>
        product.name.toLowerCase().includes(value) || product.sku.toLowerCase().includes(value),
    );
  }, [activePage, products, query]);

  function goToPage(key: PageKey) {
    setActivePage(key);
    setMobileMenuOpen(false);
  }

  async function adjustInventory(productId: string, delta: number) {
    const updated = await api<ApiInventory>(`/inventory/${productId}/adjust`, {
      method: "POST",
      body: JSON.stringify({ delta_available: delta }),
    });
    const next = mapApiInventory(updated);
    setInventory((current) => {
      const exists = current.some((item) => item.productId === productId);
      return exists
        ? current.map((item) => (item.productId === productId ? next : item))
        : [...current, next];
    });
  }

  async function createPaymentLink(orderId: string) {
    await api<PaymentLinkResponse>(`/orders/${orderId}/payment-link`, { method: "POST" });
    await loadOrders();
  }

  function addAppointment() {
    setAppointments((current) => [
      {
        id: `apt-${Date.now()}`,
        contact: selectedConversation?.name ?? "Cliente nuevo",
        scheduledAt: "2026-05-22 09:00",
        status: "scheduled",
        owner: "IA",
      },
      ...current,
    ]);
    setActivePage("appointments");
  }

  async function refreshInbox() {
    await loadInbox({ showLoading: true });
  }

  async function sendInboxMessage(content: string) {
    if (!selectedConversation) {
      return;
    }
    setInboxError("");
    await api<{ meta_message_id: string | null }>("/whatsapp/messages", {
      method: "POST",
      body: JSON.stringify({
        to: selectedConversation.phone,
        body: content,
      }),
    });
    await refreshInbox();
    const detail = await api<ApiConversationDetail>(`/conversations/${selectedConversation.id}`);
    setConversationMessages(detail.messages.map(mapApiMessage));
  }

  async function assignConversationFunnel(
    conversationId: string,
    funnelId: string | null,
    funnelStepId: string | null,
    currentStep: string | null,
  ) {
    await api<ApiConversation>(`/conversations/${conversationId}/assign-funnel`, {
      method: "POST",
      body: JSON.stringify({
        funnel_id: funnelId,
        funnel_step_id: funnelStepId,
        current_step: currentStep,
      }),
    });
    await loadInbox();
    if (selectedConversationIdRef.current === conversationId) {
      await loadConversationDetail(conversationId, false);
    }
  }

  function requestHuman() {
    if (!selectedConversation) {
      return;
    }
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === selectedConversation.id
          ? { ...conversation, state: "Handoff", assigned: "Equipo comercial" }
          : conversation,
      ),
    );
  }

  function logout() {
    setToken(null);
    setCurrentUser(null);
  }

  if (!token) {
    return <LoginPage />;
  }

  if (authLoading || !currentUser) {
    return <LoadingScreen />;
  }

  return (
    <div className="min-h-screen bg-[#edf3ef] text-ink">
      <div className="flex min-h-screen">
        <Sidebar activePage={activePage} onNavigate={goToPage} />

        {mobileMenuOpen ? (
          <div className="fixed inset-0 z-40 bg-ink/30 lg:hidden">
            <div className="h-full w-80 max-w-[88vw] bg-white px-4 py-5">
              <div className="mb-5 flex items-center justify-between">
                <Brand />
                <button
                  className="grid h-9 w-9 place-items-center rounded border border-line"
                  onClick={() => setMobileMenuOpen(false)}
                  title="Cerrar menu"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <NavList activePage={activePage} onNavigate={goToPage} />
            </div>
          </div>
        ) : null}

        <main className="flex min-w-0 flex-1 flex-col">
          <header className="flex min-h-16 items-center justify-between border-b border-line bg-white px-4 py-3 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <button
                className="grid h-9 w-9 shrink-0 place-items-center rounded border border-line bg-white text-slate-600 lg:hidden"
                title="Abrir menu"
                onClick={() => setMobileMenuOpen(true)}
              >
                <PanelLeft className="h-4 w-4" />
              </button>
              <div className="min-w-0">
                <h1 className="text-lg font-semibold">{page.title}</h1>
                <p className="text-xs text-slate-500">{page.subtitle}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                className="grid h-9 w-9 place-items-center rounded border border-line bg-white text-slate-600 shadow-soft"
                title={theme === "dark" ? "Activar modo claro" : "Activar modo oscuro"}
                onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
              >
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
              <label className="hidden h-9 items-center gap-2 rounded border border-line bg-white px-3 text-sm text-slate-600 shadow-soft md:flex">
                <Search className="h-4 w-4" />
                <input
                  className="w-40 bg-transparent outline-none"
                  placeholder="Buscar"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
              <button
                className="relative grid h-9 w-9 place-items-center rounded border border-line bg-white text-slate-600 shadow-soft"
                title={
                  totalUnread
                    ? `${totalUnread} mensajes sin leer`
                    : "Notificaciones"
                }
              >
                <Bell className="h-4 w-4" />
                {totalUnread ? (
                  <span className="absolute -right-1 -top-1 grid min-h-5 min-w-5 place-items-center rounded-full bg-danger px-1 text-[11px] font-semibold text-white">
                    {totalUnread > 99 ? "99+" : totalUnread}
                  </span>
                ) : null}
              </button>
              <button
                className="hidden h-9 items-center gap-2 rounded border border-line bg-white px-3 text-sm text-slate-600 shadow-soft sm:inline-flex"
                title="Cuenta"
                onClick={() => setActivePage("settings")}
              >
                <UserRound className="h-4 w-4" />
                <span className="max-w-32 truncate">{currentUser.name}</span>
              </button>
              <button
                className="grid h-9 w-9 place-items-center rounded bg-brand text-white shadow-soft"
                title="Cerrar sesion"
                onClick={logout}
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </header>

          <div className="p-4 lg:p-8">
            {activePage === "dashboard" ? (
              <DashboardPage
                conversations={conversations}
                orders={orders}
                appointments={appointments}
                onNavigate={setActivePage}
              />
            ) : null}
            {activePage === "inbox" ? (
              <InboxPage
                conversations={conversations}
                selectedConversation={selectedConversation}
                messages={conversationMessages}
                loading={inboxLoading}
                error={inboxError}
                onSelect={setSelectedConversationId}
                onRefresh={refreshInbox}
                onSendMessage={sendInboxMessage}
                onRequestHuman={requestHuman}
                onAddAppointment={addAppointment}
                funnels={funnels}
                onAssignFunnel={assignConversationFunnel}
              />
            ) : null}
            {activePage === "products" ? (
              <ProductsPage products={filteredProducts} inventory={inventory} onRefreshProducts={loadCatalogData} />
            ) : null}
            {activePage === "inventory" ? (
              <InventoryPage products={products} inventory={inventory} onAdjust={adjustInventory} />
            ) : null}
            {activePage === "orders" ? (
              <OrdersPage
                orders={orders}
                onCreatePaymentLink={createPaymentLink}
                onRefresh={loadOrders}
              />
            ) : null}
            {activePage === "appointments" ? (
              <AppointmentsPage appointments={appointments} onAddAppointment={addAppointment} />
            ) : null}
            {activePage === "funnels" ? (
              <FunnelsPage
                onUpdated={async () => {
                  const nextFunnels = await api<ApiFunnel[]>("/funnels");
                  setFunnels(nextFunnels);
                  await loadInbox();
                }}
              />
            ) : null}
            {activePage === "ai" ? <AiPage /> : null}
            {activePage === "whatsapp" ? <WhatsAppPage /> : null}
            {activePage === "integrations" ? <IntegrationsPage /> : null}
            {activePage === "settings" ? <SettingsPage currentUser={currentUser} /> : null}
          </div>
        </main>
      </div>
    </div>
  );
}

function LoginPage() {
  const setToken = useAuthStore((state) => state.setToken);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await api<TokenResponse>("/auth/login", {
        method: "POST",
        auth: false,
        body: JSON.stringify({ email, password }),
      });
      setToken(response.access_token);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible iniciar sesion");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-[#edf3ef] px-4 py-8 text-ink lg:grid-cols-[1fr_420px]">
      <section className="flex min-h-[420px] flex-col justify-between rounded border border-line bg-white p-6 shadow-soft lg:rounded-r-none lg:border-r-0 lg:p-10">
        <Brand />
        <div className="max-w-2xl">
          <p className="text-sm font-medium text-brand">Plataforma multitenant</p>
          <h1 className="mt-3 text-3xl font-semibold md:text-5xl">SwaFlow</h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-slate-600">
            Operacion comercial por WhatsApp con usuarios por empresa, acceso administrador y
            superusuario Swateck para soporte transversal.
          </p>
        </div>
        <div className="grid gap-3 text-sm text-slate-600 md:grid-cols-3">
          <MetricPill label="Auth" value="JWT" />
          <MetricPill label="Passwords" value="bcrypt" />
          <MetricPill label="Tenant" value="company_id" />
        </div>
      </section>

      <section className="flex items-center rounded border border-line bg-white p-6 shadow-soft lg:rounded-l-none lg:p-8">
        <form className="w-full space-y-5" onSubmit={submit}>
          <div>
            <h2 className="text-xl font-semibold">Ingreso</h2>
            <p className="mt-1 text-sm text-slate-500">Usuario y contrasena</p>
          </div>
          <label className="block">
            <span className="text-xs font-medium text-slate-500">Usuario</span>
            <input
              className="mt-1 h-11 w-full rounded border border-line bg-white px-3 text-sm outline-none focus:border-brand"
              autoComplete="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-500">Contrasena</span>
            <input
              className="mt-1 h-11 w-full rounded border border-line bg-white px-3 text-sm outline-none focus:border-brand"
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error ? (
            <div className="flex items-start gap-2 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}
          <button
            className="inline-flex h-11 w-full items-center justify-center gap-2 rounded bg-brand px-4 text-sm font-medium text-white disabled:opacity-60"
            disabled={submitting}
          >
            <LogIn className="h-4 w-4" />
            {submitting ? "Ingresando" : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}

function LoadingScreen() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#edf3ef] text-ink">
      <div className="rounded border border-line bg-white px-5 py-4 text-sm shadow-soft">
        Validando sesion
      </div>
    </main>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-10 w-10 place-items-center rounded bg-brand text-white">
        <Sparkles className="h-5 w-5" />
      </div>
      <div>
        <p className="text-sm font-semibold">Swatek Flow AI</p>
        <p className="text-xs text-slate-500">Ventas por WhatsApp</p>
      </div>
    </div>
  );
}

function Sidebar({
  activePage,
  onNavigate,
}: {
  activePage: PageKey;
  onNavigate: (page: PageKey) => void;
}) {
  return (
    <aside className="hidden w-72 shrink-0 border-r border-line bg-white px-4 py-5 lg:block">
      <div className="mb-7 px-2">
        <Brand />
      </div>
      <NavList activePage={activePage} onNavigate={onNavigate} />
    </aside>
  );
}

function NavList({
  activePage,
  onNavigate,
}: {
  activePage: PageKey;
  onNavigate: (page: PageKey) => void;
}) {
  return (
    <nav className="space-y-1">
      {navItems.map((item) => (
        <button
          key={item.key}
          className={`flex h-10 w-full items-center gap-3 rounded px-3 text-left text-sm transition ${
            item.key === activePage
              ? "bg-[#e5f3ee] font-medium text-brand"
              : "text-slate-600 hover:bg-panel hover:text-ink"
          }`}
          title={item.label}
          onClick={() => onNavigate(item.key)}
        >
          <item.icon className="h-4 w-4" />
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}

function DashboardPage({
  conversations,
  orders,
  appointments,
  onNavigate,
}: {
  conversations: Conversation[];
  orders: Order[];
  appointments: Appointment[];
  onNavigate: (page: PageKey) => void;
}) {
  const paidTotal = orders
    .filter((order) => order.status === "paid")
    .reduce((total, order) => total + order.total, 0);
  const waitingPayment = orders.filter((order) => order.status === "waiting_payment").length;
  const metrics = [
    { label: "Conversaciones abiertas", value: String(conversations.length), tone: "text-brand" },
    { label: "Ordenes en pago", value: String(waitingPayment), tone: "text-warn" },
    { label: "Ventas confirmadas", value: formatMoney(paidTotal), tone: "text-ink" },
    { label: "Citas agendadas", value: String(appointments.length), tone: "text-danger" },
  ];
  const pipeline = ["Mensaje recibido", "Intencion detectada", "Stock validado", "Link de pago enviado"];

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
      <section className="min-w-0 space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <article key={metric.label} className="rounded border border-line bg-white p-4 shadow-soft">
              <p className="text-xs font-medium text-slate-500">{metric.label}</p>
              <p className={`mt-3 text-2xl font-semibold ${metric.tone}`}>{metric.value}</p>
            </article>
          ))}
        </div>

        <section className="rounded border border-line bg-white shadow-soft">
          <SectionHeader
            title="Inbox activo"
            subtitle="Conversaciones que requieren accion"
            action={
              <IconButton title="Ver inbox" onClick={() => onNavigate("inbox")}>
                <Inbox className="h-4 w-4" />
              </IconButton>
            }
          />
          <div className="divide-y divide-line">
            {conversations.map((conversation) => (
              <article key={conversation.id} className="grid gap-3 px-4 py-4 sm:grid-cols-[220px_1fr_100px]">
                <div>
                  <p className="text-sm font-medium">{conversation.name}</p>
                  <p className="text-xs text-slate-500">{conversation.phone}</p>
                </div>
                <p className="min-w-0 text-sm text-slate-600">{conversation.message}</p>
                <StatusBadge value={conversation.state} />
              </article>
            ))}
          </div>
        </section>

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Flujo de compra</h2>
            <CreditCard className="h-4 w-4 text-brand" />
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            {pipeline.map((step, index) => (
              <div key={step} className="rounded border border-line bg-panel p-3">
                <div className="mb-3 flex h-8 w-8 items-center justify-center rounded bg-white text-sm font-semibold text-brand">
                  {index + 1}
                </div>
                <p className="text-sm font-medium">{step}</p>
              </div>
            ))}
          </div>
        </section>
      </section>

      <aside className="space-y-5">
        <InfoPanel title="IA comercial" icon={Bot}>
          <KeyValue label="Clasificador" value="Activo" strong />
          <KeyValue label="Tools simuladas" value="4" />
          <KeyValue label="Handoff humano" value="Listo" />
        </InfoPanel>
        <InfoPanel title="Equipo" icon={UserRound}>
          {["Owner", "Admin", "Agent"].map((role) => (
            <KeyValue key={role} label={role} value="Listo" />
          ))}
        </InfoPanel>
      </aside>
    </div>
  );
}

function InboxPage({
  conversations,
  selectedConversation,
  messages,
  loading,
  error,
  onSelect,
  onRefresh,
  onSendMessage,
  onRequestHuman,
  onAddAppointment,
  funnels,
  onAssignFunnel,
}: {
  conversations: Conversation[];
  selectedConversation: Conversation | null;
  messages: InboxMessage[];
  loading: boolean;
  error: string;
  onSelect: (id: string) => void;
  onRefresh: () => Promise<void>;
  onSendMessage: (content: string) => Promise<void>;
  onRequestHuman: () => void;
  onAddAppointment: () => void;
  funnels: ApiFunnel[];
  onAssignFunnel: (
    conversationId: string,
    funnelId: string | null,
    funnelStepId: string | null,
    currentStep: string | null,
  ) => Promise<void>;
}) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const [assigningFunnel, setAssigningFunnel] = useState(false);

  async function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content) {
      return;
    }
    setSendError("");
    setSending(true);
    try {
      await onSendMessage(content);
      setDraft("");
    } catch (caught) {
      setSendError(caught instanceof Error ? caught.message : "No fue posible enviar el mensaje");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="grid h-[calc(100vh-112px)] gap-5 overflow-hidden xl:grid-cols-[360px_1fr]">
      <section className="flex min-h-0 flex-col overflow-hidden rounded border border-line bg-white shadow-soft">
        <SectionHeader
          title="Conversaciones"
          subtitle={loading ? "Actualizando" : `${conversations.length} activas`}
          action={
            <IconButton title="Actualizar" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4" />
            </IconButton>
          }
        />
        {error ? <div className="border-b border-line px-4 py-3 text-sm text-red-600">{error}</div> : null}
        <div className="min-h-0 flex-1 divide-y divide-line overflow-y-auto">
          {conversations.length ? (
            conversations.map((conversation) => (
              <button
                key={conversation.id}
                className={`block w-full px-4 py-4 text-left transition ${
                  selectedConversation?.id === conversation.id ? "bg-[#e5f3ee]" : "hover:bg-panel"
                }`}
                onClick={() => onSelect(conversation.id)}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2">
                    <p className="min-w-0 truncate text-sm font-medium">{conversation.name}</p>
                    {conversation.unreadCount ? (
                      <span className="grid min-h-5 min-w-5 shrink-0 place-items-center rounded-full bg-brand px-1 text-[11px] font-semibold text-white">
                        {conversation.unreadCount > 99 ? "99+" : conversation.unreadCount}
                      </span>
                    ) : null}
                  </div>
                  <StatusBadge value={conversation.state} />
                </div>
                <p className="mt-1 text-xs text-slate-500">{conversation.phone}</p>
                <p className="mt-2 line-clamp-2 text-sm text-slate-600">{conversation.message}</p>
              </button>
            ))
          ) : (
            <div className="px-4 py-8 text-sm text-slate-500">
              {loading ? "Cargando conversaciones" : "Aun no hay conversaciones"}
            </div>
          )}
        </div>
      </section>

      <section className="flex min-h-0 flex-col overflow-hidden rounded border border-line bg-white shadow-soft">
        {selectedConversation ? (
          <>
            <SectionHeader
              title={selectedConversation.name}
              subtitle={`${selectedConversation.phone} - asignado a ${selectedConversation.assigned}`}
              action={<StatusBadge value={selectedConversation.state} />}
            />
            <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
              <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-2">
                {messages.length ? (
                  messages.map((message) => (
                    <MessageBubble key={message.id} side={message.side} text={message.text} />
                  ))
                ) : (
                  <p className="text-sm text-slate-500">Sin mensajes en esta conversacion</p>
                )}
              </div>

              <div className="grid shrink-0 gap-3 sm:grid-cols-2">
                <button className="h-10 rounded border border-line px-3 text-sm" onClick={onRequestHuman}>
                  Pasar a humano
                </button>
                <button className="h-10 rounded border border-line px-3 text-sm" onClick={onAddAppointment}>
                  Agendar cita
                </button>
              </div>

              <div className="grid shrink-0 gap-3 md:grid-cols-[1fr_1fr_auto]">
                <select
                  className="h-10 rounded border border-line bg-white px-3 text-sm outline-none focus:border-brand"
                  value={selectedConversation.funnelId ?? ""}
                  onChange={async (event) => {
                    const nextFunnelId = event.target.value || null;
                    const selectedFunnel = funnels.find((funnel) => funnel.id === nextFunnelId) ?? null;
                    const firstStep = selectedFunnel?.steps?.[0] ?? null;
                    setAssigningFunnel(true);
                    try {
                      await onAssignFunnel(
                        selectedConversation.id,
                        nextFunnelId,
                        firstStep?.id ?? null,
                        firstStep?.code ?? null,
                      );
                    } finally {
                      setAssigningFunnel(false);
                    }
                  }}
                >
                  <option value="">Sin funnel</option>
                  {funnels.map((funnel) => (
                    <option key={funnel.id} value={funnel.id}>
                      {funnel.name}
                    </option>
                  ))}
                </select>
                <select
                  className="h-10 rounded border border-line bg-white px-3 text-sm outline-none focus:border-brand"
                  value={selectedConversation.funnelStepId ?? ""}
                  disabled={!selectedConversation.funnelId || assigningFunnel}
                  onChange={async (event) => {
                    const selectedFunnel = funnels.find(
                      (funnel) => funnel.id === selectedConversation.funnelId,
                    );
                    const nextStep =
                      selectedFunnel?.steps.find((step) => step.id === event.target.value) ?? null;
                    setAssigningFunnel(true);
                    try {
                      await onAssignFunnel(
                        selectedConversation.id,
                        selectedConversation.funnelId,
                        nextStep?.id ?? null,
                        nextStep?.code ?? null,
                      );
                    } finally {
                      setAssigningFunnel(false);
                    }
                  }}
                >
                  <option value="">Paso no definido</option>
                  {(funnels.find((funnel) => funnel.id === selectedConversation.funnelId)?.steps ?? []).map(
                    (step) => (
                      <option key={step.id} value={step.id}>
                        {step.position}. {step.name}
                      </option>
                    ),
                  )}
                </select>
                <div className="flex items-center text-xs text-slate-500">
                  {assigningFunnel
                    ? "Actualizando funnel..."
                    : selectedConversation.funnelName
                      ? `${selectedConversation.funnelName}${selectedConversation.funnelStepName ? ` / ${selectedConversation.funnelStepName}` : ""}`
                      : "Sin clasificacion"}
                </div>
              </div>

              <form className="grid shrink-0 gap-3 sm:grid-cols-[1fr_auto]" onSubmit={submitMessage}>
                <input
                  className="h-11 rounded border border-line bg-white px-3 text-sm outline-none focus:border-brand"
                  placeholder="Escribe una respuesta"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                />
                <button
                  className="h-11 rounded bg-brand px-4 text-sm font-medium text-white disabled:opacity-60"
                  disabled={sending || !draft.trim()}
                >
                  {sending ? "Enviando" : "Enviar"}
                </button>
              </form>
              {sendError ? <p className="text-sm text-red-600">{sendError}</p> : null}
            </div>
          </>
        ) : (
          <div className="grid min-h-0 flex-1 place-items-center p-8 text-sm text-slate-500">
            Selecciona una conversacion
          </div>
        )}
      </section>
    </div>
  );
}

function ProductsPage({
  products,
  inventory,
  onRefreshProducts,
}: {
  products: Product[];
  inventory: InventoryItem[];
  onRefreshProducts: () => Promise<void>;
}) {
  const [catalogId, setCatalogId] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function syncCatalogProducts() {
    if (!catalogId.trim()) {
      return;
    }
    setSyncing(true);
    setNotice("");
    setError("");
    try {
      const response = await api<{ fetched: number; created: number; updated: number; warning?: string | null }>(
        "/whatsapp/catalog/sync",
        {
          method: "POST",
          body: JSON.stringify({ catalog_id: catalogId.trim() }),
        },
      );
      await onRefreshProducts();
      setNotice(
        `Actualizacion completada: ${response.fetched} leidos, ${response.created} creados, ${response.updated} actualizados`,
      );
      if (response.warning) {
        setError(response.warning);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible actualizar el catalogo");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="space-y-5">
      <section className="rounded border border-line bg-white p-4 shadow-soft">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Actualizacion de catalogo</h2>
          <MessageSquareText className="h-4 w-4 text-brand" />
        </div>
        <div className="mt-4 flex items-end gap-2">
          <TextInput label="Catalog ID Meta" value={catalogId} onChange={setCatalogId} />
          <button
            className="h-10 rounded bg-brand px-4 text-sm font-medium text-white disabled:opacity-60"
            type="button"
            disabled={syncing || !catalogId.trim()}
            onClick={syncCatalogProducts}
          >
            {syncing ? "Actualizando..." : "Actualizar catalogo"}
          </button>
        </div>
        {notice ? <p className="mt-3 text-sm text-emerald-700">{notice}</p> : null}
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      </section>

      <section className="rounded border border-line bg-white shadow-soft">
        <SectionHeader title="Catalogo" subtitle="Productos sincronizados desde Meta para la IA" />
        <DataTable
          headers={["Producto", "SKU", "Precio", "Disponible real", "Estado"]}
          rows={products.map((product) => {
            const stock = inventory.find((item) => item.productId === product.id);
            return [
              product.name,
              product.sku,
              formatMoney(product.price, product.currency),
              String(Math.max(0, (stock?.available ?? 0) - (stock?.reserved ?? 0))),
              product.status,
            ];
          })}
        />
      </section>
    </div>
  );
}

function InventoryPage({
  products,
  inventory,
  onAdjust,
}: {
  products: Product[];
  inventory: InventoryItem[];
  onAdjust: (productId: string, delta: number) => Promise<void>;
}) {
  const [busyProductId, setBusyProductId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const rows = products.map((product) => {
    const item = inventory.find((candidate) => candidate.productId === product.id);
    const available = item?.available ?? 0;
    const reserved = item?.reserved ?? 0;
    const realAvailable = Math.max(0, available - reserved);
    return {
      id: product.id,
      product: product.name,
      available,
      reserved,
      realAvailable,
    };
  });

  async function adjust(productId: string, delta: number) {
    setBusyProductId(productId);
    setError("");
    try {
      await onAdjust(productId, delta);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible actualizar el inventario");
    } finally {
      setBusyProductId(null);
    }
  }

  return (
    <section className="rounded border border-line bg-white shadow-soft">
      <SectionHeader title="Stock" subtitle="Inventario sincronizado con el catalogo de productos" />
      {error ? <p className="border-b border-line px-4 py-3 text-sm text-red-600">{error}</p> : null}
      <div className="divide-y divide-line">
        {rows.map((row) => (
          <article key={row.id} className="grid gap-3 px-4 py-4 md:grid-cols-[1fr_120px_120px_150px]">
            <div>
              <p className="text-sm font-medium">{row.product}</p>
              <p className="text-xs text-slate-500">Disponible real: {row.realAvailable}</p>
            </div>
            <MetricPill label="Stock" value={String(row.available)} />
            <MetricPill label="Reservado" value={String(row.reserved)} />
            <div className="flex items-center gap-2">
              <button
                className="h-9 w-9 rounded border border-line disabled:opacity-60"
                disabled={busyProductId === row.id || row.available <= 0}
                onClick={() => void adjust(row.id, -1)}
              >
                -
              </button>
              <button
                className="h-9 w-9 rounded border border-line disabled:opacity-60"
                disabled={busyProductId === row.id}
                onClick={() => void adjust(row.id, 1)}
              >
                +
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function OrdersPage({
  orders,
  onCreatePaymentLink,
  onRefresh,
}: {
  orders: Order[];
  onCreatePaymentLink: (orderId: string) => Promise<void>;
  onRefresh: () => Promise<void>;
}) {
  const [busyOrderId, setBusyOrderId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function generateLink(orderId: string) {
    setBusyOrderId(orderId);
    setNotice("");
    setError("");
    try {
      await onCreatePaymentLink(orderId);
      setNotice("Link de pago generado y guardado en la orden.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible generar el link de pago");
    } finally {
      setBusyOrderId(null);
    }
  }

  async function refresh() {
    setError("");
    try {
      await onRefresh();
      setNotice("Ordenes actualizadas.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible actualizar las ordenes");
    }
  }

  async function copyPaymentLink(paymentLink: string) {
    await navigator.clipboard.writeText(paymentLink);
    setNotice("Link de pago copiado.");
  }

  return (
    <div className="space-y-4">
      {error ? <Notice tone="error" message={error} /> : null}
      {notice ? <Notice tone="success" message={notice} /> : null}
      <section className="rounded border border-line bg-white shadow-soft">
        <SectionHeader
          title="Ordenes"
          subtitle="Links Wompi persistidos, vencimiento y estados de pago"
          action={
            <button
              className="inline-flex h-9 items-center gap-2 rounded border border-line px-3 text-sm"
              onClick={() => void refresh()}
            >
              <RefreshCw className="h-4 w-4" />
              Actualizar
            </button>
          }
        />
        {orders.length ? (
          <div className="divide-y divide-line">
            {orders.map((order) => (
              <article
                key={order.id}
                className="grid gap-3 px-4 py-4 lg:grid-cols-[150px_1fr_130px_130px_minmax(220px,1fr)]"
              >
                <div>
                  <p className="text-sm font-medium">#{order.id.slice(0, 8)}</p>
                  <p className="text-xs text-slate-500">{new Date(order.createdAt).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-700">{order.contact}</p>
                  <p className="text-xs text-slate-500">{order.paymentReference ?? "Sin referencia"}</p>
                </div>
                <p className="text-sm font-medium">{formatMoney(order.total)}</p>
                <div className="space-y-1">
                  <StatusBadge value={order.status} />
                  <p className="text-xs text-slate-500">{order.paymentStatus}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {order.paymentLink ? (
                    <>
                      <a
                        className="inline-flex h-9 items-center gap-2 rounded border border-line px-3 text-sm"
                        href={order.paymentLink}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <ExternalLink className="h-4 w-4" />
                        Abrir link
                      </a>
                      <button
                        className="grid h-9 w-9 place-items-center rounded border border-line"
                        title="Copiar link de pago"
                        onClick={() => void copyPaymentLink(order.paymentLink!)}
                      >
                        <ClipboardCopy className="h-4 w-4" />
                      </button>
                      {order.paymentExpiresAt ? (
                        <p className="w-full text-xs text-slate-500">
                          Vence: {new Date(order.paymentExpiresAt).toLocaleString()}
                        </p>
                      ) : null}
                    </>
                  ) : (
                    <button
                      className="h-9 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-50"
                      disabled={order.status === "paid" || busyOrderId === order.id}
                      onClick={() => void generateLink(order.id)}
                    >
                      {busyOrderId === order.id ? "Generando..." : "Generar link"}
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="px-4 py-10 text-center text-sm text-slate-500">
            Aun no hay ordenes. Los links de pago generados apareceran aqui.
          </div>
        )}
      </section>
    </div>
  );
}

function AppointmentsPage({
  appointments,
  onAddAppointment,
}: {
  appointments: Appointment[];
  onAddAppointment: () => void;
}) {
  return (
    <section className="rounded border border-line bg-white shadow-soft">
      <SectionHeader
        title="Agenda"
        subtitle="Citas comerciales por cliente"
        action={
          <button className="inline-flex h-9 items-center gap-2 rounded bg-brand px-3 text-sm font-medium text-white" onClick={onAddAppointment}>
            <Plus className="h-4 w-4" />
            Cita
          </button>
        }
      />
      <DataTable
        headers={["Cliente", "Fecha", "Estado", "Asesor"]}
        rows={appointments.map((appointment) => [
          appointment.contact,
          appointment.scheduledAt,
          appointment.status,
          appointment.owner,
        ])}
      />
    </section>
  );
}

function FunnelsPage({ onUpdated }: { onUpdated: () => Promise<void> }) {
  const [funnels, setFunnels] = useState<ApiFunnel[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selectedFunnelId, setSelectedFunnelId] = useState<string | null>(null);
  const [name, setName] = useState("Funnel principal");
  const [description, setDescription] = useState("Embudo comercial para WhatsApp.");
  const [steps, setSteps] = useState<
    Array<{ position: number; name: string; code: string; prompt: string; transition_criteria: string }>
  >([
    {
      position: 1,
      name: "Bienvenida",
      code: "bienvenida",
      prompt: "Da la bienvenida al cliente y detecta su interes principal.",
      transition_criteria: "Cliente expresa necesidad o interes concreto.",
    },
    {
      position: 2,
      name: "Detectar intencion",
      code: "detectar_intencion",
      prompt: "Clasifica la intencion: compra, soporte, agenda o humano.",
      transition_criteria: "Intencion principal identificada.",
    },
    {
      position: 3,
      name: "Propuesta",
      code: "propuesta",
      prompt: "Presenta la mejor recomendacion y siguiente paso.",
      transition_criteria: "Cliente confirma accion siguiente.",
    },
  ]);
  const [sampleMessage, setSampleMessage] = useState(
    "Quiero comprar una camiseta negra y agendar una cita",
  );
  const [intent, setIntent] = useState<AiClassifyResponse | null>(null);
  const [classifying, setClassifying] = useState(false);
  const [classifyError, setClassifyError] = useState("");

  const loadFunnels = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api<ApiFunnel[]>("/funnels");
      setFunnels(response);
      const selected = response[0] ?? null;
      setSelectedFunnelId(selected?.id ?? null);
      if (selected) {
        setName(selected.name);
        setDescription(selected.description ?? "");
        setSteps(
          selected.steps.map((step) => ({
            position: step.position,
            name: step.name,
            code: step.code,
            prompt: step.prompt,
            transition_criteria: step.transition_criteria,
          })),
        );
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible cargar funnels");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadFunnels();
  }, [loadFunnels]);

  async function saveFunnel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const payload = {
        name,
        description,
        status: "active",
        is_default: true,
        steps: steps.map((step) => ({
          position: step.position,
          name: step.name,
          code: step.code,
          prompt: step.prompt,
          objectives: [],
          transition_criteria: step.transition_criteria,
          status: "active",
          config: {},
        })),
      };
      if (selectedFunnelId) {
        await api<ApiFunnel>(`/funnels/${selectedFunnelId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        await api<ApiFunnel>("/funnels", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      setNotice("Funnel guardado");
      await loadFunnels();
      await onUpdated();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible guardar funnel");
    } finally {
      setSaving(false);
    }
  }

  async function classifySample() {
    const content = sampleMessage.trim();
    if (!content) {
      return;
    }
    setClassifying(true);
    setClassifyError("");
    try {
      const response = await api<AiClassifyResponse>("/ai/classify", {
        method: "POST",
        body: JSON.stringify({ message: content }),
      });
      setIntent(response);
    } catch (caught) {
      const fallback = classifyIntent(content);
      setIntent({ intent: fallback.intent, confidence: Number(fallback.confidence), entities: {} });
      setClassifyError(caught instanceof Error ? caught.message : "No fue posible clasificar con la API");
    } finally {
      setClassifying(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <section className="rounded border border-line bg-white shadow-soft">
        <SectionHeader
          title="Funnels del tenant"
          subtitle={loading ? "Cargando" : `${funnels.length} configurados`}
          action={
            <button
              className="inline-flex h-9 items-center gap-2 rounded bg-brand px-3 text-sm font-medium text-white"
              onClick={() => {
                setSelectedFunnelId(null);
                setName("Nuevo funnel");
                setDescription("");
              }}
            >
              <Plus className="h-4 w-4" />
              Nuevo
            </button>
          }
        />
        <div className="divide-y divide-line">
          {funnels.map((funnel) => (
            <button
              key={funnel.id}
              className={`block w-full px-4 py-3 text-left ${
                funnel.id === selectedFunnelId ? "bg-[#e5f3ee]" : "hover:bg-panel"
              }`}
              onClick={() => {
                setSelectedFunnelId(funnel.id);
                setName(funnel.name);
                setDescription(funnel.description ?? "");
                setSteps(
                  funnel.steps.map((step) => ({
                    position: step.position,
                    name: step.name,
                    code: step.code,
                    prompt: step.prompt,
                    transition_criteria: step.transition_criteria,
                  })),
                );
              }}
            >
              <p className="text-sm font-semibold">{funnel.name}</p>
              <p className="text-xs text-slate-500">{funnel.steps.length} pasos</p>
            </button>
          ))}
        </div>
      </section>

      <form className="space-y-5" onSubmit={saveFunnel}>
        {error ? <Notice tone="error" message={error} /> : null}
        {notice ? <Notice tone="success" message={notice} /> : null}
        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="grid gap-3 md:grid-cols-2">
            <TextInput label="Nombre funnel" value={name} onChange={setName} />
            <TextInput label="Descripcion" value={description} onChange={setDescription} />
          </div>
        </section>
        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Pasos del funnel</h2>
            <button
              className="inline-flex h-9 items-center gap-2 rounded border border-line px-3 text-sm"
              type="button"
              onClick={() =>
                setSteps((current) => [
                  ...current,
                  {
                    position: current.length + 1,
                    name: `Paso ${current.length + 1}`,
                    code: `paso_${current.length + 1}`,
                    prompt: "",
                    transition_criteria: "",
                  },
                ])
              }
            >
              <Plus className="h-4 w-4" />
              Nuevo paso
            </button>
          </div>
          <div className="space-y-3">
            {steps.map((step, index) => (
              <article key={`${step.code}-${index}`} className="rounded border border-line bg-panel p-3">
                <div className="grid gap-3 md:grid-cols-3">
                  <TextInput
                    label="Paso"
                    value={String(step.position)}
                    onChange={(value) =>
                      setSteps((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, position: Number(value) || 1 } : item,
                        ),
                      )
                    }
                  />
                  <TextInput
                    label="Nombre"
                    value={step.name}
                    onChange={(value) =>
                      setSteps((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, name: value } : item,
                        ),
                      )
                    }
                  />
                  <TextInput
                    label="Codigo"
                    value={step.code}
                    onChange={(value) =>
                      setSteps((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, code: value } : item,
                        ),
                      )
                    }
                  />
                </div>
                <div className="mt-3 grid gap-3">
                  <TextAreaInput
                    label="Prompt del paso"
                    value={step.prompt}
                    minHeight="min-h-20"
                    onChange={(value) =>
                      setSteps((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, prompt: value } : item,
                        ),
                      )
                    }
                  />
                  <TextAreaInput
                    label="Criterio de transicion"
                    value={step.transition_criteria}
                    minHeight="min-h-16"
                    onChange={(value) =>
                      setSteps((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, transition_criteria: value } : item,
                        ),
                      )
                    }
                  />
                </div>
              </article>
            ))}
          </div>
          <div className="mt-4">
            <button
              className="inline-flex h-10 items-center gap-2 rounded bg-brand px-4 text-sm font-medium text-white disabled:opacity-60"
              disabled={saving}
            >
              <Save className="h-4 w-4" />
              {saving ? "Guardando" : "Guardar funnel"}
            </button>
          </div>
        </section>

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Prueba de clasificacion (funnel)</h2>
            <Bot className="h-4 w-4 text-brand" />
          </div>
          <textarea
            className="mt-4 min-h-28 w-full rounded border border-line p-3 text-sm outline-none focus:border-brand"
            value={sampleMessage}
            onChange={(event) => setSampleMessage(event.target.value)}
          />
          <button
            className="mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
            type="button"
            disabled={classifying || !sampleMessage.trim()}
            onClick={() => void classifySample()}
          >
            <Search className="h-4 w-4" />
            {classifying ? "Analizando" : "Clasificar"}
          </button>
          {classifyError ? <p className="mt-3 text-sm text-red-600">{classifyError}</p> : null}
          <div className="mt-4 rounded border border-line bg-panel p-3">
            <KeyValue label="Intencion" value={intent?.intent ?? "-"} strong />
            <KeyValue
              label="Confianza"
              value={intent ? `${Math.round(intent.confidence * 100)}%` : "-"}
            />
            <KeyValue
              label="Entidades"
              value={intent ? String(Object.keys(intent.entities ?? {}).length) : "-"}
            />
          </div>
        </section>
      </form>
    </div>
  );
}

function AiPage() {
  const [agents, setAgents] = useState<AiAgentResponse[]>([]);
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [form, setForm] = useState<AiAgentForm>({ ...defaultAiAgentForm });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [toasts, setToasts] = useState<ToastState[]>([]);
  const [faqEntries, setFaqEntries] = useState<AiFaqEntry[]>([]);
  const [faqQuestionDraft, setFaqQuestionDraft] = useState("");
  const [faqAnswerDraft, setFaqAnswerDraft] = useState("");
  const [faqUploadFile, setFaqUploadFile] = useState<File | null>(null);
  const [faqUploading, setFaqUploading] = useState(false);
  const [faqSavingId, setFaqSavingId] = useState<string | null>(null);
  const [faqDeletingId, setFaqDeletingId] = useState<string | null>(null);
  const [interactiveTemplates, setInteractiveTemplates] = useState<AiInteractiveTemplate[]>([]);
  const [interactiveSaving, setInteractiveSaving] = useState(false);
  const [interactiveEditingId, setInteractiveEditingId] = useState<string | null>(null);
  const [interactiveDeletingId, setInteractiveDeletingId] = useState<string | null>(null);
  const [interactiveHighlightedId, setInteractiveHighlightedId] = useState<string | null>(null);
  const [interactiveForm, setInteractiveForm] = useState(createInteractiveTemplateForm);

  const checklist = aiChecklist(form);
  const completedItems = checklist.filter((item) => item.done).length;
  const maturity = Math.round((completedItems / checklist.length) * 100);
  const canCreateFaq = faqEntries.length < 10;
  const activeAgent = activeAgentId
    ? agents.find((agent) => agent.id === activeAgentId) ?? null
    : null;

  const loadAgents = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const nextAgents = await api<AiAgentResponse[]>("/ai/agents");
      const selected = nextAgents.find((agent) => agent.active) ?? nextAgents[0] ?? null;
      setAgents(nextAgents);
      setActiveAgentId(selected?.id ?? null);
      setForm(aiFormFromAgent(selected));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible cargar el agente");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadInteractiveTemplates = useCallback(async () => {
    try {
      const rows = await api<AiInteractiveTemplate[]>("/ai/interactive-templates");
      setInteractiveTemplates(rows);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible cargar las plantillas");
    }
  }, []);

  const loadFaqEntries = useCallback(async () => {
    try {
      const rows = await api<AiFaqEntry[]>("/ai/faqs");
      setFaqEntries(rows);
    } catch {
      setFaqEntries([]);
    }
  }, []);

  useEffect(() => {
    void loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    void loadInteractiveTemplates();
  }, [loadInteractiveTemplates]);

  useEffect(() => {
    void loadFaqEntries();
  }, [loadFaqEntries]);

  useEffect(() => {
    if (!notice) {
      return;
    }
    const toast: ToastState = { id: Date.now(), tone: "success", message: notice };
    setToasts((current) => [...current, toast]);
    const timer = window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== toast.id));
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    if (!error) {
      return;
    }
    const toast: ToastState = { id: Date.now() + 1, tone: "error", message: error };
    setToasts((current) => [...current, toast]);
    const timer = window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== toast.id));
    }, 4500);
    return () => window.clearTimeout(timer);
  }, [error]);

  function updateField<K extends keyof AiAgentForm>(field: K, value: AiAgentForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function selectAgent(agentId: string) {
    const selected = agents.find((agent) => agent.id === agentId) ?? null;
    setActiveAgentId(selected?.id ?? null);
    setForm(aiFormFromAgent(selected));
    setNotice("");
    setError("");
  }

  async function saveAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setNotice("");
    setError("");
    try {
      const payload = aiPayloadFromForm(form);
      const saved = activeAgent
        ? await api<AiAgentResponse>(`/ai/agents/${activeAgent.id}`, {
            method: "PUT",
            body: JSON.stringify(payload),
          })
        : await api<AiAgentResponse>("/ai/agents", {
            method: "POST",
            body: JSON.stringify(payload),
          });
      setNotice("Agente guardado");
      setActiveAgentId(saved.id);
      await loadAgents();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible guardar el agente");
    } finally {
      setSaving(false);
    }
  }

  async function saveInteractiveTemplate() {
    const options = [interactiveForm.option1, interactiveForm.option2, interactiveForm.option3]
      .map((title, index) => ({ id: `${interactiveForm.action_key}_opt_${index + 1}`, title: title.trim() }))
      .filter((item) => item.title);
    if (!interactiveForm.name.trim() || !interactiveForm.action_key.trim() || !interactiveForm.body_text.trim()) {
      return;
    }
    if (options.length === 0) {
      return;
    }
    setInteractiveSaving(true);
    setError("");
    setNotice("");
    try {
      const payload = {
        name: interactiveForm.name.trim(),
        action_key: interactiveForm.action_key.trim(),
        template_type: interactiveForm.template_type,
        body_text: interactiveForm.body_text.trim(),
        footer_text: interactiveForm.footer_text.trim() || null,
        button_text:
          interactiveForm.template_type === "list" ? interactiveForm.button_text.trim() || "Ver opciones" : null,
        section_title:
          interactiveForm.template_type === "list"
            ? interactiveForm.section_title.trim() || "Opciones"
            : null,
        usage_instruction: interactiveForm.usage_instruction.trim(),
        trigger_mode: interactiveForm.trigger_mode,
        trigger_fields:
          interactiveForm.trigger_mode === "after_capture"
            ? interactiveForm.trigger_fields
                .split(",")
                .map((field) => field.trim().toLowerCase())
                .filter(Boolean)
            : [],
        options,
        active: true,
      };
      if (interactiveEditingId) {
        const updated = await api<AiInteractiveTemplate>(`/ai/interactive-templates/${interactiveEditingId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        setInteractiveTemplates((current) =>
          [updated, ...current.filter((item) => item.id !== updated.id)],
        );
        setInteractiveHighlightedId(updated.id);
      } else {
        const created = await api<AiInteractiveTemplate>("/ai/interactive-templates", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setInteractiveTemplates((current) => [created, ...current.filter((item) => item.id !== created.id)]);
        setInteractiveHighlightedId(created.id);
      }
      setNotice(interactiveEditingId ? "Plantilla actualizada" : "Plantilla interactiva guardada");
      setInteractiveEditingId(null);
      setInteractiveForm(createInteractiveTemplateForm());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible guardar plantilla");
    } finally {
      setInteractiveSaving(false);
    }
  }

  useEffect(() => {
    if (!interactiveHighlightedId) {
      return;
    }
    const timer = window.setTimeout(() => setInteractiveHighlightedId(null), 3500);
    return () => window.clearTimeout(timer);
  }, [interactiveHighlightedId]);

  function editInteractiveTemplate(template: AiInteractiveTemplate) {
    setInteractiveEditingId(template.id);
    setInteractiveForm({
      name: template.name,
      action_key: template.action_key,
      template_type: template.template_type,
      body_text: template.body_text,
      footer_text: template.footer_text ?? "",
      button_text: template.button_text ?? "Ver opciones",
      section_title: template.section_title ?? "Opciones",
      usage_instruction: template.usage_instruction ?? "",
      trigger_mode: template.trigger_mode ?? "ai_decides",
      trigger_fields: (template.trigger_fields ?? []).join(", "),
      option1: template.options[0]?.title ?? "",
      option2: template.options[1]?.title ?? "",
      option3: template.options[2]?.title ?? "",
    });
  }

  function cancelInteractiveEdit() {
    setInteractiveEditingId(null);
    setInteractiveForm(createInteractiveTemplateForm());
  }

  async function deleteInteractiveTemplate(templateId: string) {
    setInteractiveDeletingId(templateId);
    setError("");
    setNotice("");
    try {
      await api<unknown>(`/ai/interactive-templates/${templateId}`, { method: "DELETE" });
      setInteractiveTemplates((current) => current.filter((item) => item.id !== templateId));
      if (interactiveEditingId === templateId) {
        cancelInteractiveEdit();
      }
      await loadInteractiveTemplates().catch(() => null);
      setNotice("Plantilla eliminada");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible eliminar plantilla");
    } finally {
      setInteractiveDeletingId(null);
    }
  }

  function updateFaqLocal(faqId: string, field: "question" | "answer", value: string) {
    setFaqEntries((current) =>
      current.map((entry) => (entry.id === faqId ? { ...entry, [field]: value } : entry)),
    );
  }

  async function createFaqEntry() {
    const question = faqQuestionDraft.trim();
    const answer = faqAnswerDraft.trim();
    if (!question || !answer || !canCreateFaq) {
      return;
    }
    setError("");
    setNotice("");
    try {
      const created = await api<AiFaqEntry>("/ai/faqs", {
        method: "POST",
        body: JSON.stringify({ question, answer, active: true }),
      });
      setFaqEntries((current) => [...current, created]);
      setFaqQuestionDraft("");
      setFaqAnswerDraft("");
      setNotice("FAQ agregada");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible agregar FAQ");
    }
  }

  async function saveFaqEntry(entry: AiFaqEntry) {
    setFaqSavingId(entry.id);
    setError("");
    setNotice("");
    try {
      const saved = await api<AiFaqEntry>(`/ai/faqs/${entry.id}`, {
        method: "PUT",
        body: JSON.stringify({
          question: entry.question,
          answer: entry.answer,
          active: entry.active,
        }),
      });
      setFaqEntries((current) => current.map((item) => (item.id === saved.id ? saved : item)));
      setNotice("FAQ actualizada");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible actualizar FAQ");
    } finally {
      setFaqSavingId(null);
    }
  }

  async function removeFaqEntry(faqId: string) {
    setFaqDeletingId(faqId);
    setError("");
    setNotice("");
    try {
      await api<unknown>(`/ai/faqs/${faqId}`, { method: "DELETE" });
      setFaqEntries((current) => current.filter((item) => item.id !== faqId));
      setNotice("FAQ eliminada");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible eliminar FAQ");
    } finally {
      setFaqDeletingId(null);
    }
  }

  async function uploadFaqFile() {
    if (!faqUploadFile) {
      return;
    }
    setFaqUploading(true);
    setError("");
    setNotice("");
    try {
      const formData = new FormData();
      formData.append("file", faqUploadFile);
      const result = await api<AiFaqUploadResult>("/ai/faqs/upload", {
        method: "POST",
        body: formData,
      });
      await loadFaqEntries();
      setFaqUploadFile(null);
      setNotice(
        `FAQ cargadas: ${result.total_read} leidas, ${result.created} nuevas, ${result.updated} actualizadas.`,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible cargar el archivo FAQ");
    } finally {
      setFaqUploading(false);
    }
  }

  return (
    <>
      <ToastStack toasts={toasts} />
      <form className="space-y-5" onSubmit={saveAgent}>
        <div className="min-w-0 space-y-5">
        {error ? <Notice tone="error" message={error} /> : null}
        {notice ? <Notice tone="success" message={notice} /> : null}

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              <div className="grid h-12 w-12 shrink-0 place-items-center rounded bg-[#e5f3ee] text-brand">
                <BrainCircuit className="h-6 w-6" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-base font-semibold">{form.name || "Agente IA"}</h2>
                  <StatusBadge value={form.active ? "active" : "paused"} />
                </div>
                <p className="mt-1 text-sm text-slate-500">Configura como conversa el agente y su contexto base.</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {agents.length ? (
                <select
                  className="h-10 rounded border border-line bg-white px-3 text-sm outline-none focus:border-brand"
                  value={activeAgentId ?? ""}
                  onChange={(event) => selectAgent(event.target.value)}
                >
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              ) : null}
              <button
                className="inline-flex h-10 items-center gap-2 rounded border border-line px-3 text-sm"
                type="button"
                onClick={() => {
                  setActiveAgentId(null);
                  setForm({ ...defaultAiAgentForm, name: "Nuevo agente comercial" });
                }}
              >
                <Plus className="h-4 w-4" />
                Nuevo
              </button>
              <button
                className="inline-flex h-10 items-center gap-2 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
                disabled={saving || loading}
              >
                <Save className="h-4 w-4" />
                {saving ? "Guardando" : "Guardar"}
              </button>
            </div>
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-[1.2fr_1fr]">
            <div className="rounded border border-line bg-panel p-3">
              <p className="text-xs font-medium uppercase text-slate-500">Mensaje inicial</p>
              <textarea
                className="mt-2 min-h-20 w-full resize-y rounded border border-line bg-white p-3 text-sm outline-none focus:border-brand"
                value={form.welcomeMessage}
                onChange={(event) => updateField("welcomeMessage", event.target.value)}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <TextInput label="Nombre" value={form.name} onChange={(value) => updateField("name", value)} />
              <SelectInput
                label="Estado"
                value={form.active ? "active" : "paused"}
                options={[
                  { value: "active", label: "Activo" },
                  { value: "paused", label: "Pausado" },
                ]}
                onChange={(value) => updateField("active", value === "active")}
              />
              <TextInput
                label="Personalidad"
                value={form.personality}
                onChange={(value) => updateField("personality", value)}
              />
              <TextInput label="Tono" value={form.tone} onChange={(value) => updateField("tone", value)} />
              <TextInput
                label="Idioma"
                value={form.language}
                onChange={(value) => updateField("language", value)}
              />
              <TextInput
                label="Horario"
                value={form.schedule}
                onChange={(value) => updateField("schedule", value)}
              />
            </div>
          </div>
        </section>

        <InfoPanel title="Madurez de la IA" icon={Gauge}>
          <div>
            <div className="mb-2 flex items-end justify-between">
              <span className="text-2xl font-semibold text-brand">{maturity}%</span>
              <span className="text-xs text-slate-500">
                {completedItems}/{checklist.length}
              </span>
            </div>
            <ProgressBar value={maturity} />
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {checklist.map((item) => (
              <ChecklistItem key={item.label} label={item.label} done={item.done} />
            ))}
          </div>
        </InfoPanel>

        <InfoPanel title="Modelo de IA" icon={BrainCircuit}>
          <div className="grid gap-3 md:grid-cols-[minmax(240px,1fr)_180px_180px_180px]">
            <SelectInput
              label="Modelo"
              value={form.model}
              options={[
                { value: "gpt-4o-mini", label: "gpt-4o-mini" },
                { value: "gpt-4o", label: "gpt-4o" },
                { value: "gpt-4.1-mini", label: "gpt-4.1-mini" },
              ]}
              onChange={(value) => updateField("model", value)}
            />
            <TextInput
              label="Temperatura"
              value={form.temperature}
              onChange={(value) => updateField("temperature", value)}
            />
            <TextInput
              label="Max tokens"
              value={form.maxTokens}
              onChange={(value) => updateField("maxTokens", value)}
            />
            <div className="rounded border border-line bg-panel px-3 py-2">
              <KeyValue label="API global" value="Conectada" strong />
            </div>
          </div>
        </InfoPanel>

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">Contexto del negocio</h2>
              <p className="text-xs text-slate-500">Informacion que el agente usa en cada respuesta</p>
            </div>
            <BookOpen className="h-4 w-4 text-brand" />
          </div>
          <div className="mt-4 grid gap-4">
            <TextAreaInput
              label="Descripcion"
              value={form.businessDescription}
              minHeight="min-h-28"
              onChange={(value) => updateField("businessDescription", value)}
            />
            <TextAreaInput
              label="Productos / servicios"
              value={form.productsServices}
              minHeight="min-h-32"
              onChange={(value) => updateField("productsServices", value)}
            />
            <TextAreaInput
              label="Objetivo de conversacion"
              value={form.conversationObjective}
              minHeight="min-h-20"
              onChange={(value) => updateField("conversationObjective", value)}
            />
          </div>
        </section>

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Guion conversacional</h2>
              <p className="text-xs text-slate-500">
                Define etapas, condiciones y Action key para que el agente ejecute el siguiente paso en el momento correcto.
              </p>
            </div>
            <Workflow className="h-4 w-4 text-brand" />
          </div>
          <textarea
            className="min-h-52 w-full resize-y rounded border border-line bg-panel p-3 text-sm outline-none focus:border-brand"
            value={form.conversationGuide}
            onChange={(event) => updateField("conversationGuide", event.target.value)}
            placeholder={"1. Datos iniciales completos:\n   Enviar el interactivo menu_principal.\n\n2. Cliente elige productos:\n   Consultar catalogo e inventario y enviar cards."}
          />
          <p className="mt-2 text-xs text-slate-500">
            Para llamar botones o listas escribe el Action key exacto de la biblioteca, por ejemplo: menu_principal.
          </p>
        </section>

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Prompt del sistema</h2>
              <p className="text-xs text-slate-500">Instruccion principal para el agente</p>
            </div>
            <ShieldCheck className="h-4 w-4 text-brand" />
          </div>
          <textarea
            className="min-h-48 w-full resize-y rounded border border-line bg-panel p-3 text-sm outline-none focus:border-brand"
            value={form.systemPrompt}
            onChange={(event) => updateField("systemPrompt", event.target.value)}
          />
        </section>

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Reglas de seguridad</h2>
              <p className="text-xs text-slate-500">
                Guardado en base de datos del agente y aplicado por la IA en cada respuesta
              </p>
            </div>
            <ShieldCheck className="h-4 w-4 text-brand" />
          </div>
          <textarea
            className="min-h-28 w-full resize-y rounded border border-line bg-panel p-3 text-sm outline-none focus:border-brand"
            value={form.securityRules}
            onChange={(event) => updateField("securityRules", event.target.value)}
          />
        </section>

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold">Preguntas frecuentes</h2>
              <p className="text-xs text-slate-500">Maximo 10 por tenant. Carga por archivo o edita manual.</p>
            </div>
            <StatusBadge value={`${faqEntries.length}/10`} />
          </div>

          <div className="mt-4 rounded border border-line bg-panel p-3">
            <p className="mb-2 text-xs font-medium uppercase text-slate-500">Cargar archivo FAQ</p>
            <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
              <input
                className="h-10 w-full rounded border border-line bg-white px-3 text-sm file:mr-3 file:rounded file:border-0 file:bg-panel file:px-2 file:py-1 file:text-xs"
                type="file"
                accept=".csv,.txt,.json,.xlsx"
                onChange={(event) => setFaqUploadFile(event.target.files?.[0] ?? null)}
              />
              <button
                className="h-10 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
                type="button"
                disabled={faqUploading || !faqUploadFile}
                onClick={() => void uploadFaqFile()}
              >
                {faqUploading ? "Cargando..." : "Cargar archivo"}
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-500">Formato: columns question/answer o pregunta/respuesta.</p>
          </div>

          <div className="mt-4 rounded border border-line bg-panel p-3">
            <p className="mb-2 text-xs font-medium uppercase text-slate-500">Nueva pregunta frecuente</p>
            <div className="grid gap-3 md:grid-cols-2">
              <TextInput label="Pregunta" value={faqQuestionDraft} onChange={setFaqQuestionDraft} />
              <TextInput label="Respuesta" value={faqAnswerDraft} onChange={setFaqAnswerDraft} />
            </div>
            <button
              className="mt-3 h-9 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
              type="button"
              disabled={!canCreateFaq || !faqQuestionDraft.trim() || !faqAnswerDraft.trim()}
              onClick={() => void createFaqEntry()}
            >
              Agregar FAQ
            </button>
          </div>

          <div className="mt-4 space-y-3">
            {faqEntries.length ? (
              faqEntries.map((entry) => (
                <div key={entry.id} className="rounded border border-line bg-panel p-3">
                  <div className="grid gap-3 md:grid-cols-2">
                    <TextInput
                      label="Pregunta"
                      value={entry.question}
                      onChange={(value) => updateFaqLocal(entry.id, "question", value)}
                    />
                    <TextInput
                      label="Respuesta"
                      value={entry.answer}
                      onChange={(value) => updateFaqLocal(entry.id, "answer", value)}
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      className="h-9 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
                      type="button"
                      disabled={faqSavingId === entry.id}
                      onClick={() => void saveFaqEntry(entry)}
                    >
                      {faqSavingId === entry.id ? "Guardando..." : "Guardar"}
                    </button>
                    <button
                      className="h-9 rounded border border-line px-3 text-sm disabled:opacity-60"
                      type="button"
                      disabled={faqDeletingId === entry.id}
                      onClick={() => void removeFaqEntry(entry.id)}
                    >
                      {faqDeletingId === entry.id ? "Eliminando..." : "Eliminar"}
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No hay FAQs cargadas.</p>
            )}
          </div>
        </section>

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Biblioteca de interactivos</h2>
            <MessageSquareText className="h-4 w-4 text-brand" />
          </div>
          <p className="mt-1 text-xs text-slate-500">
            SwaFlow entrega estas plantillas al agente y traduce cada Action key al formato tecnico de WhatsApp.
          </p>
          <div className="mt-3 rounded border border-line bg-panel p-3 text-xs text-slate-700">
            <p className="font-semibold text-slate-900">Contrato estandar para interactivos</p>
            <p className="mt-1">
              Para un envio fijo usa <strong>Automatico al capturar datos</strong>. Para una decision comercial usa
              <strong> La IA decide segun instruccion</strong> y describe el momento en la regla de uso.
            </p>
            <p className="mt-1">
              En el prompt escribe una instruccion legible, por ejemplo:{" "}
              <code className="rounded bg-white px-1 py-0.5 text-brand">
                Despues de capturar nombre, email y ciudad, envia el interactivo menu_principal.
              </code>
            </p>
            <p className="mt-1">No pegues JSON en el prompt. Usa siempre el Action key visible en cada plantilla.</p>
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-[360px_1fr]">
            <div className="rounded border border-line bg-panel p-3">
              <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
                <span>Plantillas creadas</span>
                <span>{interactiveTemplates.length}</span>
              </div>
              <p className="mt-1 text-xs text-slate-500">Se muestran al guardar. Usa scroll para ver mas.</p>
              <div className="mt-3 max-h-[390px] space-y-2 overflow-y-auto pr-1">
                {interactiveTemplates.length ? (
                  interactiveTemplates.map((item) => (
                    <div
                      key={item.id}
                      className={`rounded border p-3 text-sm transition-colors ${
                        item.id === interactiveHighlightedId
                          ? "border-brand bg-[#e5f3ee]"
                          : "border-line bg-white"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate font-medium">{item.name}</p>
                          <p className="truncate text-xs text-brand">{item.action_key}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {item.template_type === "buttons" ? "Botones" : "Lista"} · {item.options.length} opciones
                          </p>
                          <p className="mt-2 text-xs text-slate-700">{item.body_text}</p>
                          <p className="mt-2 text-xs text-slate-500">
                            {item.trigger_mode === "after_capture"
                              ? `Automatico al capturar: ${(item.trigger_fields ?? []).join(", ")}`
                              : item.usage_instruction || "La IA decide segun el contexto"}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {item.options.map((option) => (
                              <span
                                key={option.id}
                                className="inline-flex min-h-7 items-center rounded-full border border-brand bg-[#e5f3ee] px-2.5 py-1 text-xs font-medium text-brand"
                              >
                                {option.title}
                              </span>
                            ))}
                          </div>
                          {item.footer_text ? (
                            <p className="mt-2 text-xs text-slate-500">{item.footer_text}</p>
                          ) : null}
                        </div>
                        <div className="flex shrink-0 gap-1">
                          <button
                            className="grid h-8 w-8 place-items-center rounded border border-line bg-white text-slate-600 disabled:opacity-50"
                            type="button"
                            title="Editar plantilla"
                            onClick={() => editInteractiveTemplate(item)}
                            disabled={interactiveSaving || interactiveDeletingId === item.id}
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            className="grid h-8 w-8 place-items-center rounded border border-line bg-white text-red-600 disabled:opacity-50"
                            type="button"
                            title="Eliminar plantilla"
                            onClick={() => void deleteInteractiveTemplate(item.id)}
                            disabled={interactiveDeletingId === item.id}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">Sin plantillas interactivas.</p>
                )}
              </div>
            </div>

            <div className="min-w-0">
              <div className="grid gap-3 md:grid-cols-2">
                <TextInput
                  label="Nombre de plantilla"
                  value={interactiveForm.name}
                  onChange={(value) => setInteractiveForm((current) => ({ ...current, name: value }))}
                />
                <TextInput
                  label="Action key"
                  value={interactiveForm.action_key}
                  onChange={(value) =>
                    setInteractiveForm((current) => ({
                      ...current,
                      action_key: value.toLowerCase().replace(/\s+/g, "_"),
                    }))
                  }
                />
                <SelectInput
                  label="Tipo"
                  value={interactiveForm.template_type}
                  options={[
                    { value: "buttons", label: "Botones" },
                    { value: "list", label: "Lista" },
                  ]}
                  onChange={(value) =>
                    setInteractiveForm((current) => ({ ...current, template_type: value as "buttons" | "list" }))
                  }
                />
                <TextInput
                  label="Texto principal"
                  value={interactiveForm.body_text}
                  onChange={(value) => setInteractiveForm((current) => ({ ...current, body_text: value }))}
                />
                <SelectInput
                  label="Momento de envio"
                  value={interactiveForm.trigger_mode}
                  options={[
                    { value: "ai_decides", label: "La IA decide segun instruccion" },
                    { value: "after_capture", label: "Automatico al capturar datos" },
                  ]}
                  onChange={(value) =>
                    setInteractiveForm((current) => ({
                      ...current,
                      trigger_mode: value as "ai_decides" | "after_capture",
                    }))
                  }
                />
                {interactiveForm.trigger_mode === "after_capture" ? (
                  <TextInput
                    label="Campos requeridos separados por coma"
                    value={interactiveForm.trigger_fields}
                    placeholder="nombre, email, ciudad"
                    onChange={(value) => setInteractiveForm((current) => ({ ...current, trigger_fields: value }))}
                  />
                ) : null}
                <TextInput
                  label="Opcion 1"
                  value={interactiveForm.option1}
                  onChange={(value) => setInteractiveForm((current) => ({ ...current, option1: value }))}
                />
                <TextInput
                  label="Opcion 2"
                  value={interactiveForm.option2}
                  onChange={(value) => setInteractiveForm((current) => ({ ...current, option2: value }))}
                />
                <TextInput
                  label="Opcion 3"
                  value={interactiveForm.option3}
                  onChange={(value) => setInteractiveForm((current) => ({ ...current, option3: value }))}
                />
                <TextInput
                  label="Footer (opcional)"
                  value={interactiveForm.footer_text}
                  onChange={(value) => setInteractiveForm((current) => ({ ...current, footer_text: value }))}
                />
              </div>
              <div className="mt-3">
                <TextAreaInput
                  label="Instruccion de uso para la IA"
                  value={interactiveForm.usage_instruction}
                  minHeight="min-h-20"
                  onChange={(value) =>
                    setInteractiveForm((current) => ({ ...current, usage_instruction: value }))
                  }
                />
              </div>
              {interactiveForm.template_type === "list" ? (
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <TextInput
                    label="Texto boton lista"
                    value={interactiveForm.button_text}
                    onChange={(value) => setInteractiveForm((current) => ({ ...current, button_text: value }))}
                  />
                  <TextInput
                    label="Titulo de seccion"
                    value={interactiveForm.section_title}
                    onChange={(value) => setInteractiveForm((current) => ({ ...current, section_title: value }))}
                  />
                </div>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  className="h-10 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
                  type="button"
                  disabled={interactiveSaving}
                  onClick={() => void saveInteractiveTemplate()}
                >
                  {interactiveSaving
                    ? "Guardando..."
                    : interactiveEditingId
                      ? "Actualizar plantilla"
                      : "Guardar plantilla"}
                </button>
                {interactiveEditingId ? (
                  <button
                    className="h-10 rounded border border-line px-3 text-sm"
                    type="button"
                    onClick={cancelInteractiveEdit}
                  >
                    Cancelar edicion
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        </section>

      </div>
      </form>
    </>
  );
}

function WhatsAppPage() {
  const [setup, setSetup] = useState<WhatsAppSetup | null>(null);
  const [accounts, setAccounts] = useState<WhatsAppAccount[]>([]);
  const [phoneNumberId, setPhoneNumberId] = useState("");
  const [businessAccountId, setBusinessAccountId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [verifyToken, setVerifyToken] = useState("");
  const [testPhone, setTestPhone] = useState("");
  const [testBody, setTestBody] = useState("Hola, esta es una prueba de SwaFlow.");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [sending, setSending] = useState(false);

  const activeAccount = accounts[0];

  useEffect(() => {
    let cancelled = false;
    Promise.all([api<WhatsAppSetup>("/whatsapp/setup"), api<WhatsAppAccount[]>("/whatsapp/accounts")])
      .then(([setupResponse, accountsResponse]) => {
        if (cancelled) {
          return;
        }
        setSetup(setupResponse);
        setAccounts(accountsResponse);
        const account = accountsResponse[0];
        if (account) {
          setPhoneNumberId(account.phone_number_id);
          setBusinessAccountId(account.business_account_id ?? "");
          setVerifyToken(account.verify_token);
        } else {
          setVerifyToken(setupResponse.verify_token ?? "");
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "No fue posible cargar WhatsApp");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshAccounts() {
    const nextAccounts = await api<WhatsAppAccount[]>("/whatsapp/accounts");
    setAccounts(nextAccounts);
    return nextAccounts;
  }

  async function saveAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSaving(true);
    try {
      const webhookVerifyToken = setup?.verify_token ?? verifyToken;
      await api<WhatsAppAccount>("/whatsapp/accounts", {
        method: "POST",
        body: JSON.stringify({
          phone_number_id: phoneNumberId,
          business_account_id: businessAccountId || null,
          access_token: accessToken,
          verify_token: webhookVerifyToken || null,
        }),
      });
      const nextAccounts = await refreshAccounts();
      setAccessToken("");
      setVerifyToken(nextAccounts[0]?.verify_token ?? webhookVerifyToken ?? "");
      setMessage(nextAccounts[0] ? "Cuenta guardada" : "Cuenta creada");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible guardar la cuenta");
    } finally {
      setSaving(false);
    }
  }

  async function testAccount() {
    if (!activeAccount) {
      setError("Guarda primero la cuenta");
      return;
    }
    setError("");
    setMessage("");
    setTesting(true);
    try {
      const response = await api<WhatsAppAccountTest>(`/whatsapp/accounts/${activeAccount.id}/test`, {
        method: "POST",
      });
      setMessage(
        `Meta OK: ${response.display_phone_number ?? response.phone_number_id} - ${response.quality_rating ?? "sin rating"}`,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Meta rechazo las credenciales");
    } finally {
      setTesting(false);
    }
  }

  async function sendTestMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSending(true);
    try {
      const response = await api<{ meta_message_id: string | null }>("/whatsapp/messages", {
        method: "POST",
        body: JSON.stringify({
          to: testPhone,
          body: testBody,
          account_id: activeAccount?.id ?? null,
        }),
      });
      setMessage(`Mensaje enviado${response.meta_message_id ? `: ${response.meta_message_id}` : ""}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible enviar el mensaje");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
      <div className="space-y-5">
        {error ? <Notice tone="error" message={error} /> : null}
        {message ? <Notice tone="success" message={message} /> : null}

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <h2 className="text-sm font-semibold">Cuenta Cloud API</h2>
          <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={saveAccount}>
            <TextInput label="Phone number ID" value={phoneNumberId} onChange={setPhoneNumberId} />
            <TextInput label="Business account ID" value={businessAccountId} onChange={setBusinessAccountId} />
            <TextInput label="Verify token SwaFlow" value={verifyToken} readOnly />
            <PasswordInput label="Access token" value={accessToken} onChange={setAccessToken} />
            <div className="md:col-span-2">
              <button
                className="inline-flex h-9 items-center gap-2 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
                disabled={saving}
              >
                <Save className="h-4 w-4" />
                {saving ? "Guardando" : "Guardar"}
              </button>
            </div>
          </form>
        </section>

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">Prueba de envio</h2>
            <button
              className="h-9 rounded border border-line px-3 text-sm disabled:opacity-60"
              disabled={testing || !activeAccount}
              onClick={testAccount}
            >
              {testing ? "Probando" : "Probar Meta"}
            </button>
          </div>
          <form className="mt-4 grid gap-3 md:grid-cols-[220px_1fr_auto]" onSubmit={sendTestMessage}>
            <TextInput label="Destino" value={testPhone} onChange={setTestPhone} />
            <TextInput label="Mensaje" value={testBody} onChange={setTestBody} />
            <div className="flex items-end">
              <button
                className="h-10 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
                disabled={sending || !activeAccount}
              >
                {sending ? "Enviando" : "Enviar"}
              </button>
            </div>
          </form>
        </section>

        <section className="rounded border border-line bg-white shadow-soft">
          <SectionHeader title="Cuentas" subtitle="Numeros activos por tenant" />
          <DataTable
            headers={["Phone ID", "WABA", "Estado"]}
            rows={accounts.map((account) => [
              account.phone_number_id,
              account.business_account_id ?? "-",
              account.status,
            ])}
          />
        </section>
      </div>

      <div className="space-y-5">
        <InfoPanel title="Webhook" icon={MessageSquareText}>
          <KeyValue label="Callback" value={setup?.callback_url ?? "-"} />
          <KeyValue label="Verify token" value={setup?.verify_token ?? "-"} />
          <KeyValue label="Graph" value={setup?.graph_api_version ?? "-"} />
          <KeyValue label="Firma" value={setup?.app_secret_configured ? "Activa" : "Pendiente"} />
        </InfoPanel>
        <InfoPanel title="Eventos" icon={CheckCircle2}>
          <KeyValue label="Entrantes" value="messages" strong />
          <KeyValue label="Estados" value="statuses" />
          <KeyValue label="Salida" value="/whatsapp/messages" />
        </InfoPanel>
      </div>
    </div>
  );
}

function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<CompanyIntegrationResponse[]>([]);
  const [webhooks, setWebhooks] = useState<OutboundWebhookResponse[]>([]);
  const [forms, setForms] = useState<Record<string, IntegrationFormValue>>(createIntegrationForms);
  const [webhookForm, setWebhookForm] = useState({
    event_type: "message.received",
    target_url: "",
    secret_token: "",
  });
  const [loading, setLoading] = useState(true);
  const [savingType, setSavingType] = useState<string | null>(null);
  const [webhookBusyId, setWebhookBusyId] = useState<string | null>(null);
  const [savingWebhook, setSavingWebhook] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const integrationByType = useMemo(
    () => new Map(integrations.map((integration) => [integration.type, integration])),
    [integrations],
  );
  const configuredCount = integrationDefinitions.filter((definition) =>
    integrationByType.has(definition.type),
  ).length;
  const wompiWebhookUrl = new URL("/webhooks/payments/wompi", window.location.origin).toString();
  const mercadoPagoWebhookUrl = new URL(
    "/webhooks/payments/mercado-pago",
    window.location.origin,
  ).toString();

  const refreshIntegrations = useCallback(
    async ({ showLoading = true }: { showLoading?: boolean } = {}) => {
      if (showLoading) {
        setLoading(true);
      }
      setError("");
      try {
        const [nextIntegrations, nextWebhooks] = await Promise.all([
          api<CompanyIntegrationResponse[]>("/integrations"),
          api<OutboundWebhookResponse[]>("/outbound-webhooks"),
        ]);
        setIntegrations(nextIntegrations);
        setWebhooks(nextWebhooks);
        setForms((current) => {
          const next = { ...current };
          integrationDefinitions.forEach((definition) => {
            const saved = nextIntegrations.find(
              (integration) => integration.type === definition.type,
            );
            const previous = current[definition.type] ?? createIntegrationForm(definition);
            next[definition.type] = {
              ...previous,
              config: {
                ...definition.defaultConfig,
                ...(saved ? stringifyConfig(saved.config) : {}),
              },
              credentials: "",
              secondaryCredentials: "",
              status: saved?.status ?? "pending",
            };
          });
          return next;
        });
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "No fue posible cargar integraciones");
      } finally {
        if (showLoading) {
          setLoading(false);
        }
      }
    },
    [],
  );

  useEffect(() => {
    void refreshIntegrations();
  }, [refreshIntegrations]);

  function updateIntegrationField(type: string, key: string, value: string) {
    setForms((current) => {
      const currentForm =
        current[type] ?? { config: {}, credentials: "", secondaryCredentials: "", status: "pending" };
      return {
        ...current,
        [type]: {
          ...currentForm,
          config: { ...currentForm.config, [key]: value },
        },
      };
    });
  }

  function updateIntegrationSecret(type: string, value: string) {
    setForms((current) => {
      const currentForm =
        current[type] ?? { config: {}, credentials: "", secondaryCredentials: "", status: "pending" };
      return {
        ...current,
        [type]: {
          ...currentForm,
          credentials: value,
        },
      };
    });
  }

  function updateIntegrationSecondarySecret(type: string, value: string) {
    setForms((current) => {
      const currentForm =
        current[type] ?? { config: {}, credentials: "", secondaryCredentials: "", status: "pending" };
      return {
        ...current,
        [type]: {
          ...currentForm,
          secondaryCredentials: value,
        },
      };
    });
  }

  function buildCredentialsPayload(definition: IntegrationDefinition, form: IntegrationFormValue) {
    const primary = form.credentials.trim();
    const secondary = form.secondaryCredentials.trim();
    if (definition.type === "payments") {
      const payload: Record<string, string> = {};
      if (primary) {
        payload.private_key = primary;
      }
      if (secondary) {
        payload.events_secret = secondary;
      }
      return Object.keys(payload).length ? JSON.stringify(payload) : "";
    }
    return primary;
  }

  async function saveIntegration(
    event: FormEvent<HTMLFormElement>,
    definition: IntegrationDefinition,
  ) {
    event.preventDefault();
    const form = forms[definition.type] ?? createIntegrationForm(definition);
    const existing = integrationByType.get(definition.type);
    const credentials = buildCredentialsPayload(definition, form);
    setSavingType(definition.type);
    setError("");
    setMessage("");
    try {
      if (existing) {
        const payload: {
          config: Record<string, string>;
          status: string;
          credentials?: string;
        } = {
          config: form.config,
          status: "active",
        };
        if (credentials) {
          payload.credentials = credentials;
        }
        await api<CompanyIntegrationResponse>(`/integrations/${existing.id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        const payload: {
          type: string;
          config: Record<string, string>;
          credentials?: string;
        } = {
          type: definition.type,
          config: form.config,
        };
        if (credentials) {
          payload.credentials = credentials;
        }
        await api<CompanyIntegrationResponse>("/integrations", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      setForms((current) => ({
        ...current,
        [definition.type]: {
          ...(current[definition.type] ?? createIntegrationForm(definition)),
          credentials: "",
          secondaryCredentials: "",
          status: "active",
        },
      }));
      setMessage(`${definition.title} guardado`);
      await refreshIntegrations({ showLoading: false });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible guardar la integracion");
    } finally {
      setSavingType(null);
    }
  }

  async function saveOutboundWebhook(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!webhookForm.target_url.trim()) {
      setError("URL destino es requerida");
      return;
    }
    setSavingWebhook(true);
    setError("");
    setMessage("");
    try {
      await api<OutboundWebhookResponse>("/outbound-webhooks", {
        method: "POST",
        body: JSON.stringify({
          event_type: webhookForm.event_type,
          target_url: webhookForm.target_url.trim(),
          secret_token: webhookForm.secret_token.trim() || null,
          active: true,
        }),
      });
      setWebhookForm((current) => ({ ...current, target_url: "", secret_token: "" }));
      setMessage("Webhook saliente guardado");
      await refreshIntegrations({ showLoading: false });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible guardar el webhook");
    } finally {
      setSavingWebhook(false);
    }
  }

  async function toggleOutboundWebhook(webhook: OutboundWebhookResponse) {
    setWebhookBusyId(webhook.id);
    setError("");
    setMessage("");
    try {
      await api<OutboundWebhookResponse>(`/outbound-webhooks/${webhook.id}`, {
        method: "PUT",
        body: JSON.stringify({ active: !webhook.active }),
      });
      await refreshIntegrations({ showLoading: false });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible actualizar el webhook");
    } finally {
      setWebhookBusyId(null);
    }
  }

  async function deleteOutboundWebhook(webhookId: string) {
    setWebhookBusyId(webhookId);
    setError("");
    setMessage("");
    try {
      await api<{ detail: string }>(`/outbound-webhooks/${webhookId}`, { method: "DELETE" });
      setMessage("Webhook eliminado");
      await refreshIntegrations({ showLoading: false });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible eliminar el webhook");
    } finally {
      setWebhookBusyId(null);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
      <div className="space-y-5">
        {error ? <Notice tone="error" message={error} /> : null}
        {message ? <Notice tone="success" message={message} /> : null}

        <div className="grid gap-5 2xl:grid-cols-2">
          {integrationDefinitions.map((definition) => {
            const form = forms[definition.type] ?? createIntegrationForm(definition);
            const existing = integrationByType.get(definition.type);
            const Icon = definition.icon;
            const secretStatus = existing?.credentials_configured ? "Secreto guardado" : "Sin secreto";
            return (
              <section
                key={definition.type}
                className="rounded border border-line bg-white p-4 shadow-soft"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded bg-[#e5f3ee] text-brand">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h2 className="text-sm font-semibold">{definition.title}</h2>
                      <p className="mt-1 text-xs text-slate-500">{definition.subtitle}</p>
                    </div>
                  </div>
                  <StatusBadge value={existing ? form.status : "pending"} />
                </div>

                <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={(event) => saveIntegration(event, definition)}>
                  {definition.fields.map((field) =>
                    field.options ? (
                      <SelectInput
                        key={field.key}
                        label={field.label}
                        value={form.config[field.key] ?? ""}
                        options={field.options}
                        onChange={(value) => updateIntegrationField(definition.type, field.key, value)}
                      />
                    ) : (
                      <TextInput
                        key={field.key}
                        label={field.label}
                        value={form.config[field.key] ?? ""}
                        placeholder={field.placeholder}
                        onChange={(value) => updateIntegrationField(definition.type, field.key, value)}
                      />
                    ),
                  )}
                  <PasswordInput
                    label={definition.secretLabel}
                    value={form.credentials}
                    onChange={(value) => updateIntegrationSecret(definition.type, value)}
                  />
                  {definition.extraSecretLabel ? (
                    <PasswordInput
                      label={definition.extraSecretLabel}
                      value={form.secondaryCredentials}
                      onChange={(value) =>
                        updateIntegrationSecondarySecret(definition.type, value)
                      }
                    />
                  ) : null}
                  <div className="flex items-end">
                    <button
                      className="inline-flex h-10 w-full items-center justify-center gap-2 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
                      disabled={savingType === definition.type}
                    >
                      <Save className="h-4 w-4" />
                      {savingType === definition.type ? "Guardando" : "Guardar"}
                    </button>
                  </div>
                  <div className="sm:col-span-2 flex items-center justify-between gap-3 border-t border-line pt-3 text-xs text-slate-500">
                    <span>{secretStatus}</span>
                    <span>{existing ? `ID ${existing.id.slice(0, 8)}` : "Pendiente por guardar"}</span>
                  </div>
                </form>
              </section>
            );
          })}
        </div>

        <section className="rounded border border-line bg-white shadow-soft">
          <SectionHeader
            title="Webhooks salientes"
            subtitle="Eventos para n8n y servicios externos"
            action={
              <IconButton title="Actualizar" onClick={() => void refreshIntegrations()}>
                <RefreshCw className="h-4 w-4" />
              </IconButton>
            }
          />
          <form className="grid gap-3 p-4 lg:grid-cols-[220px_1fr_220px_auto]" onSubmit={saveOutboundWebhook}>
            <SelectInput
              label="Evento"
              value={webhookForm.event_type}
              options={outboundEventOptions}
              onChange={(value) => setWebhookForm((current) => ({ ...current, event_type: value }))}
            />
            <TextInput
              label="URL destino"
              value={webhookForm.target_url}
              onChange={(value) => setWebhookForm((current) => ({ ...current, target_url: value }))}
            />
            <PasswordInput
              label="Secret"
              value={webhookForm.secret_token}
              onChange={(value) => setWebhookForm((current) => ({ ...current, secret_token: value }))}
            />
            <div className="flex items-end">
              <button
                className="inline-flex h-10 items-center justify-center gap-2 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
                disabled={savingWebhook}
              >
                <Plus className="h-4 w-4" />
                {savingWebhook ? "Guardando" : "Agregar"}
              </button>
            </div>
          </form>
          <div className="border-t border-line">
            {webhooks.length ? (
              <div className="divide-y divide-line">
                {webhooks.map((webhook) => (
                  <article
                    key={webhook.id}
                    className="grid gap-3 px-4 py-4 md:grid-cols-[180px_1fr_120px_100px]"
                  >
                    <div>
                      <p className="text-sm font-medium">{webhook.event_type}</p>
                      <p className="text-xs text-slate-500">
                        {webhook.secret_configured ? "Firma activa" : "Sin firma"}
                      </p>
                    </div>
                    <p className="min-w-0 break-all text-sm text-slate-600">{webhook.target_url}</p>
                    <StatusBadge value={webhook.active ? "active" : "paused"} />
                    <div className="flex items-center gap-2">
                      <button
                        className="h-9 rounded border border-line px-3 text-xs"
                        disabled={webhookBusyId === webhook.id}
                        onClick={() => void toggleOutboundWebhook(webhook)}
                      >
                        {webhook.active ? "Pausar" : "Activar"}
                      </button>
                      <IconButton title="Eliminar" onClick={() => void deleteOutboundWebhook(webhook.id)}>
                        <X className="h-4 w-4" />
                      </IconButton>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="px-4 py-8 text-sm text-slate-500">
                {loading ? "Cargando webhooks" : "Aun no hay webhooks salientes"}
              </div>
            )}
          </div>
        </section>
      </div>

      <aside className="space-y-5">
        <InfoPanel title="Estado" icon={CheckCircle2}>
          <KeyValue label="Conectores" value={`${configuredCount}/${integrationDefinitions.length}`} strong />
          <KeyValue label="Webhooks" value={String(webhooks.length)} />
          <KeyValue label="Carga" value={loading ? "Actualizando" : "Lista"} />
        </InfoPanel>
        <InfoPanel title="Pagos" icon={CreditCard}>
          <KeyValue label="Wompi" value={wompiWebhookUrl} strong />
          <KeyValue label="Mercado Pago" value={mercadoPagoWebhookUrl} />
        </InfoPanel>
        <InfoPanel title="Seguridad" icon={Link2}>
          <KeyValue label="Credenciales" value="Cifradas" strong />
          <KeyValue label="Secreto visible" value="No" />
          <KeyValue label="Tenant" value="company_id" />
        </InfoPanel>
      </aside>
    </div>
  );
}

function SettingsPage({ currentUser }: { currentUser: CurrentUser }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);

  async function submitPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordMessage("");
    setPasswordError("");
    if (newPassword !== confirmPassword) {
      setPasswordError("La confirmacion no coincide");
      return;
    }
    setSavingPassword(true);
    try {
      await api<{ detail: string }>("/auth/password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordMessage("Contrasena actualizada");
    } catch (caught) {
      setPasswordError(caught instanceof Error ? caught.message : "No fue posible actualizar");
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
      <div className="space-y-5">
        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <h2 className="text-sm font-semibold">Cuenta</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Input label="Nombre" defaultValue={currentUser.name} />
            <Input label="Usuario" defaultValue={currentUser.email} />
            <Input label="Rol actual" defaultValue={currentUser.role} />
            <Input label="Estado" defaultValue={currentUser.status} />
          </div>
        </section>

        <section className="rounded border border-line bg-white p-4 shadow-soft">
          <h2 className="text-sm font-semibold">Seguridad</h2>
          <form className="mt-4 grid gap-3 md:grid-cols-3" onSubmit={submitPassword}>
            <PasswordInput
              label="Contrasena actual"
              value={currentPassword}
              onChange={setCurrentPassword}
            />
            <PasswordInput label="Nueva contrasena" value={newPassword} onChange={setNewPassword} />
            <PasswordInput
              label="Confirmar"
              value={confirmPassword}
              onChange={setConfirmPassword}
            />
            <div className="md:col-span-3">
              {passwordError ? <p className="mb-3 text-sm text-red-600">{passwordError}</p> : null}
              {passwordMessage ? (
                <p className="mb-3 text-sm text-emerald-700">{passwordMessage}</p>
              ) : null}
              <button
                className="inline-flex h-9 items-center gap-2 rounded bg-brand px-3 text-sm font-medium text-white disabled:opacity-60"
                disabled={savingPassword}
              >
                <Save className="h-4 w-4" />
                {savingPassword ? "Guardando" : "Actualizar contrasena"}
              </button>
            </div>
          </form>
        </section>
      </div>

      <div className="space-y-5">
        <InfoPanel title="Base de datos" icon={CheckCircle2}>
          <KeyValue label="Motor" value="MariaDB 10.6" strong />
          <KeyValue label="Migracion" value="20260518_0001" />
          <KeyValue label="Tenant" value="company_id obligatorio" />
        </InfoPanel>
        <InfoPanel title="Acceso" icon={UserRound}>
          <KeyValue
            label="Superusuario"
            value={currentUser.role === "superadmin" ? "Swateck" : "No"}
            strong={currentUser.role === "superadmin"}
          />
          <KeyValue label="Tenant actual" value={currentUser.company_id.slice(0, 8)} />
          <KeyValue label="API" value={window.location.origin} />
        </InfoPanel>
      </div>
    </div>
  );
}

function SectionHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <div>
        <h2 className="text-sm font-semibold">{title}</h2>
        {subtitle ? <p className="text-xs text-slate-500">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

function IconButton({
  title,
  children,
  onClick,
}: {
  title: string;
  children: ReactNode;
  onClick?: () => void;
}) {
  return (
    <button className="grid h-9 w-9 place-items-center rounded border border-line text-slate-600" title={title} onClick={onClick}>
      {children}
    </button>
  );
}

function StatusBadge({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const tone =
    normalized.includes("paid") || normalized.includes("active") || normalized.includes("compra")
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : normalized.includes("handoff") || normalized.includes("waiting")
        ? "border-amber-200 bg-amber-50 text-amber-700"
        : "border-line bg-panel text-slate-600";
  return (
    <span className={`inline-flex h-7 items-center justify-center rounded border px-2 text-xs font-medium ${tone}`}>
      {value}
    </span>
  );
}

function InfoPanel({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: typeof Bot;
  children: ReactNode;
}) {
  return (
    <section className="rounded border border-line bg-white p-4 shadow-soft">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold">{title}</h2>
        <Icon className="h-4 w-4 text-brand" />
      </div>
      <div className="space-y-3 text-sm">{children}</div>
    </section>
  );
}

function KeyValue({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="shrink-0 text-slate-600">{label}</span>
      <span className={`min-w-0 break-all text-right ${strong ? "font-medium text-brand" : "font-medium"}`}>{value}</span>
    </div>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-line bg-panel px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-sm font-semibold">{value}</p>
    </div>
  );
}

function MessageBubble({ side, text }: { side: "left" | "right"; text: string }) {
  return (
    <div className={`flex ${side === "right" ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[680px] rounded p-3 text-sm ${side === "right" ? "bg-brand text-white" : "bg-panel text-slate-700"}`}>
        {text}
      </div>
    </div>
  );
}

function DataTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-left text-sm">
        <thead className="bg-panel text-xs uppercase text-slate-500">
          <tr>
            {headers.map((header) => (
              <th key={header} className="px-4 py-3 font-medium">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr key={row.join("-")}>
              {row.map((cell) => (
                <td key={cell} className="px-4 py-3 text-slate-700">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Input({ label, defaultValue }: { label: string; defaultValue: string }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <input
        className="mt-1 h-10 w-full rounded border border-line bg-white px-3 text-sm outline-none focus:border-brand"
        defaultValue={defaultValue}
      />
    </label>
  );
}

function Notice({ tone, message }: { tone: "error" | "success"; message: string }) {
  const isError = tone === "error";
  const Icon = isError ? AlertCircle : CheckCircle2;

  return (
    <div
      className={`flex items-start gap-2 rounded border p-3 text-sm ${
        isError
          ? "border-red-200 bg-red-50 text-red-700"
          : "border-emerald-200 bg-emerald-50 text-emerald-700"
      }`}
      role={isError ? "alert" : "status"}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

function ToastStack({ toasts }: { toasts: ToastState[] }) {
  if (!toasts.length) {
    return null;
  }
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[80] flex w-[min(92vw,420px)] flex-col gap-2">
      {toasts.map((toast) => {
        const isError = toast.tone === "error";
        const Icon = isError ? AlertCircle : CheckCircle2;
        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-2 rounded border px-3 py-2 text-sm shadow-soft ${
              isError ? "border-red-200 bg-red-50 text-red-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"
            }`}
            role={isError ? "alert" : "status"}
          >
            <Icon className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{toast.message}</span>
          </div>
        );
      })}
    </div>
  );
}

function TextAreaInput({
  label,
  value,
  onChange,
  minHeight = "min-h-28",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  minHeight?: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium uppercase text-slate-500">{label}</span>
      <textarea
        className={`mt-1 w-full resize-y rounded border border-line bg-panel p-3 text-sm outline-none focus:border-brand ${minHeight}`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-line">
      <div className="h-full rounded-full bg-brand" style={{ width: `${Math.max(0, Math.min(value, 100))}%` }} />
    </div>
  );
}

function ChecklistItem({ label, done }: { label: string; done: boolean }) {
  return (
    <div className="flex items-start gap-2 text-sm">
      <CheckCircle2 className={`mt-0.5 h-4 w-4 shrink-0 ${done ? "text-brand" : "text-slate-300"}`} />
      <span className={done ? "text-slate-700" : "text-slate-500"}>{label}</span>
    </div>
  );
}

function TextInput({
  label,
  value,
  onChange,
  placeholder,
  readOnly = false,
}: {
  label: string;
  value: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  readOnly?: boolean;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <input
        className={`mt-1 h-10 w-full rounded border border-line px-3 text-sm outline-none focus:border-brand ${
          readOnly ? "bg-panel text-slate-600" : "bg-white"
        }`}
        readOnly={readOnly}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange?.(event.target.value)}
      />
    </label>
  );
}

function SelectInput({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: IntegrationOption[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <select
        className="mt-1 h-10 w-full rounded border border-line bg-white px-3 text-sm outline-none focus:border-brand"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function PasswordInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <input
        className="mt-1 h-10 w-full rounded border border-line bg-white px-3 text-sm outline-none focus:border-brand"
        type="password"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function classifyIntent(message: string) {
  const normalized = message.toLowerCase();
  if (normalized.includes("compr") || normalized.includes("pagar")) {
    return { intent: "buy_product", confidence: "0.91" };
  }
  if (normalized.includes("cita") || normalized.includes("agenda")) {
    return { intent: "schedule_appointment", confidence: "0.86" };
  }
  if (normalized.includes("asesor") || normalized.includes("humano")) {
    return { intent: "request_human", confidence: "0.88" };
  }
  if (normalized.includes("queja") || normalized.includes("molesto")) {
    return { intent: "complaint", confidence: "0.84" };
  }
  return { intent: "unknown", confidence: "0.45" };
}

export default App;
