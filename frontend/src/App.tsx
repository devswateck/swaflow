import { useMemo, useState } from "react";
import {
  Bell,
  Bot,
  CalendarDays,
  ChartNoAxesCombined,
  CheckCircle2,
  CreditCard,
  Filter,
  Inbox,
  Link2,
  LogIn,
  MessageSquareText,
  Package,
  PanelLeft,
  Plus,
  Save,
  Search,
  Settings,
  ShoppingCart,
  Sparkles,
  UserRound,
  Warehouse,
  X,
} from "lucide-react";

type PageKey =
  | "dashboard"
  | "inbox"
  | "products"
  | "inventory"
  | "orders"
  | "appointments"
  | "ai"
  | "whatsapp"
  | "integrations"
  | "settings";

type Conversation = {
  id: string;
  name: string;
  phone: string;
  message: string;
  state: string;
  assigned: string;
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
  status: string;
  payment: string;
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

const initialConversations: Conversation[] = [
  {
    id: "conv-1",
    name: "Laura Mejia",
    phone: "+57 300 000 0001",
    message: "Quiere comprar camiseta negra talla M",
    state: "Compra",
    assigned: "IA",
  },
  {
    id: "conv-2",
    name: "Andres Rojas",
    phone: "+57 301 000 0002",
    message: "Pidio hablar con un asesor",
    state: "Handoff",
    assigned: "Carolina",
  },
  {
    id: "conv-3",
    name: "Diana Perez",
    phone: "+57 302 000 0003",
    message: "Solicita una cita para manana",
    state: "Agenda",
    assigned: "IA",
  },
];

const initialProducts: Product[] = [
  { id: "prod-1", name: "Camiseta negra", sku: "CAM-NEG-M", price: 80000, currency: "COP", status: "active" },
  { id: "prod-2", name: "Gorra premium", sku: "GOR-PRE", price: 65000, currency: "COP", status: "active" },
  { id: "prod-3", name: "Hoodie urbano", sku: "HOO-URB", price: 180000, currency: "COP", status: "active" },
];

const initialInventory: InventoryItem[] = [
  { productId: "prod-1", available: 12, reserved: 2 },
  { productId: "prod-2", available: 8, reserved: 1 },
  { productId: "prod-3", available: 5, reserved: 0 },
];

const initialOrders: Order[] = [
  { id: "ord-101", contact: "Laura Mejia", total: 80000, status: "waiting_payment", payment: "Link enviado" },
  { id: "ord-102", contact: "Felipe Torres", total: 245000, status: "paid", payment: "Confirmado" },
  { id: "ord-103", contact: "Diana Perez", total: 0, status: "pending", payment: "Sin link" },
];

const initialAppointments: Appointment[] = [
  { id: "apt-1", contact: "Diana Perez", scheduledAt: "2026-05-20 14:00", status: "scheduled", owner: "Carolina" },
  { id: "apt-2", contact: "Felipe Torres", scheduledAt: "2026-05-21 10:30", status: "confirmed", owner: "Mateo" },
];

const formatMoney = (value: number, currency = "COP") =>
  new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);

function App() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [conversations, setConversations] = useState(initialConversations);
  const [products, setProducts] = useState(initialProducts);
  const [inventory, setInventory] = useState(initialInventory);
  const [orders, setOrders] = useState(initialOrders);
  const [appointments, setAppointments] = useState(initialAppointments);
  const [selectedConversationId, setSelectedConversationId] = useState(initialConversations[0].id);

  const page = pageCopy[activePage];
  const selectedConversation = conversations.find((item) => item.id === selectedConversationId) ?? conversations[0];

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

  function addProduct() {
    const nextNumber = products.length + 1;
    const product: Product = {
      id: `prod-${Date.now()}`,
      name: `Producto nuevo ${nextNumber}`,
      sku: `SKU-${String(nextNumber).padStart(3, "0")}`,
      price: 50000,
      currency: "COP",
      status: "active",
    };
    setProducts((current) => [product, ...current]);
    setInventory((current) => [{ productId: product.id, available: 0, reserved: 0 }, ...current]);
  }

  function adjustInventory(productId: string, delta: number) {
    setInventory((current) =>
      current.map((item) =>
        item.productId === productId
          ? { ...item, available: Math.max(0, item.available + delta) }
          : item,
      ),
    );
  }

  function createPaymentLink(orderId: string) {
    setOrders((current) =>
      current.map((order) =>
        order.id === orderId
          ? { ...order, status: "waiting_payment", payment: "Link enviado" }
          : order,
      ),
    );
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
                className="grid h-9 w-9 place-items-center rounded border border-line bg-white text-slate-600 shadow-soft"
                title="Notificaciones"
              >
                <Bell className="h-4 w-4" />
              </button>
              <button
                className="grid h-9 w-9 place-items-center rounded bg-brand text-white shadow-soft"
                title="Ingresar"
                onClick={() => setActivePage("settings")}
              >
                <LogIn className="h-4 w-4" />
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
                onSelect={setSelectedConversationId}
                onRequestHuman={requestHuman}
                onAddAppointment={addAppointment}
              />
            ) : null}
            {activePage === "products" ? (
              <ProductsPage products={filteredProducts} onAddProduct={addProduct} />
            ) : null}
            {activePage === "inventory" ? (
              <InventoryPage products={products} inventory={inventory} onAdjust={adjustInventory} />
            ) : null}
            {activePage === "orders" ? (
              <OrdersPage orders={orders} onCreatePaymentLink={createPaymentLink} />
            ) : null}
            {activePage === "appointments" ? (
              <AppointmentsPage appointments={appointments} onAddAppointment={addAppointment} />
            ) : null}
            {activePage === "ai" ? <AiPage /> : null}
            {activePage === "whatsapp" ? <WhatsAppPage /> : null}
            {activePage === "integrations" ? <IntegrationsPage /> : null}
            {activePage === "settings" ? <SettingsPage /> : null}
          </div>
        </main>
      </div>
    </div>
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
  onSelect,
  onRequestHuman,
  onAddAppointment,
}: {
  conversations: Conversation[];
  selectedConversation: Conversation;
  onSelect: (id: string) => void;
  onRequestHuman: () => void;
  onAddAppointment: () => void;
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <section className="rounded border border-line bg-white shadow-soft">
        <SectionHeader
          title="Conversaciones"
          subtitle="Selecciona una conversacion"
          action={
            <IconButton title="Filtrar">
              <Filter className="h-4 w-4" />
            </IconButton>
          }
        />
        <div className="divide-y divide-line">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={`block w-full px-4 py-4 text-left transition ${
                selectedConversation.id === conversation.id ? "bg-[#e5f3ee]" : "hover:bg-panel"
              }`}
              onClick={() => onSelect(conversation.id)}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium">{conversation.name}</p>
                <StatusBadge value={conversation.state} />
              </div>
              <p className="mt-1 text-xs text-slate-500">{conversation.phone}</p>
              <p className="mt-2 text-sm text-slate-600">{conversation.message}</p>
            </button>
          ))}
        </div>
      </section>

      <section className="rounded border border-line bg-white shadow-soft">
        <SectionHeader
          title={selectedConversation.name}
          subtitle={`${selectedConversation.phone} - asignado a ${selectedConversation.assigned}`}
          action={<StatusBadge value={selectedConversation.state} />}
        />
        <div className="space-y-4 p-4">
          <MessageBubble side="left" text={selectedConversation.message} />
          <MessageBubble
            side="right"
            text="Gracias por escribirnos. Voy a validar producto, stock y la mejor opcion para ti."
          />
          <div className="grid gap-3 sm:grid-cols-3">
            <button className="h-10 rounded bg-brand px-3 text-sm font-medium text-white" onClick={onRequestHuman}>
              Pasar a humano
            </button>
            <button className="h-10 rounded border border-line px-3 text-sm" onClick={onAddAppointment}>
              Agendar cita
            </button>
            <button className="h-10 rounded border border-line px-3 text-sm">Enviar mensaje</button>
          </div>
        </div>
      </section>
    </div>
  );
}

function ProductsPage({ products, onAddProduct }: { products: Product[]; onAddProduct: () => void }) {
  return (
    <section className="rounded border border-line bg-white shadow-soft">
      <SectionHeader
        title="Catalogo"
        subtitle="Productos activos disponibles para la IA"
        action={
          <button className="inline-flex h-9 items-center gap-2 rounded bg-brand px-3 text-sm font-medium text-white" onClick={onAddProduct}>
            <Plus className="h-4 w-4" />
            Nuevo
          </button>
        }
      />
      <DataTable
        headers={["Producto", "SKU", "Precio", "Estado"]}
        rows={products.map((product) => [
          product.name,
          product.sku,
          formatMoney(product.price, product.currency),
          product.status,
        ])}
      />
    </section>
  );
}

function InventoryPage({
  products,
  inventory,
  onAdjust,
}: {
  products: Product[];
  inventory: InventoryItem[];
  onAdjust: (productId: string, delta: number) => void;
}) {
  const rows = inventory.map((item) => {
    const product = products.find((candidate) => candidate.id === item.productId);
    const realAvailable = Math.max(0, item.available - item.reserved);
    return {
      id: item.productId,
      product: product?.name ?? "Producto sin nombre",
      available: item.available,
      reserved: item.reserved,
      realAvailable,
    };
  });

  return (
    <section className="rounded border border-line bg-white shadow-soft">
      <SectionHeader title="Stock" subtitle="Ajustes rapidos para pruebas del MVP" />
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
              <button className="h-9 w-9 rounded border border-line" onClick={() => onAdjust(row.id, -1)}>
                -
              </button>
              <button className="h-9 w-9 rounded border border-line" onClick={() => onAdjust(row.id, 1)}>
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
}: {
  orders: Order[];
  onCreatePaymentLink: (orderId: string) => void;
}) {
  return (
    <section className="rounded border border-line bg-white shadow-soft">
      <SectionHeader title="Ordenes" subtitle="Estados de pago y acciones comerciales" />
      <div className="divide-y divide-line">
        {orders.map((order) => (
          <article key={order.id} className="grid gap-3 px-4 py-4 md:grid-cols-[130px_1fr_140px_140px_160px]">
            <p className="text-sm font-medium">{order.id}</p>
            <p className="text-sm text-slate-600">{order.contact}</p>
            <p className="text-sm font-medium">{formatMoney(order.total)}</p>
            <StatusBadge value={order.status} />
            <button
              className="h-9 rounded border border-line px-3 text-sm disabled:opacity-50"
              disabled={order.status === "paid"}
              onClick={() => onCreatePaymentLink(order.id)}
            >
              {order.payment}
            </button>
          </article>
        ))}
      </div>
    </section>
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

function AiPage() {
  const [message, setMessage] = useState("Quiero comprar una camiseta negra");
  const intent = classifyIntent(message);

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
      <section className="rounded border border-line bg-white p-4 shadow-soft">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Prompt comercial</h2>
          <Save className="h-4 w-4 text-brand" />
        </div>
        <textarea
          className="min-h-56 w-full resize-y rounded border border-line bg-panel p-3 text-sm outline-none focus:border-brand"
          defaultValue={
            "Eres un asistente comercial. No inventes precios, no inventes disponibilidad y usa tools antes de vender."
          }
        />
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <Input label="Tono" defaultValue="Claro y comercial" />
          <Input label="Confianza minima" defaultValue="0.70" />
          <Input label="Handoff" defaultValue="Humano si hay queja" />
        </div>
      </section>

      <section className="rounded border border-line bg-white p-4 shadow-soft">
        <h2 className="text-sm font-semibold">Clasificador</h2>
        <textarea
          className="mt-4 min-h-28 w-full rounded border border-line p-3 text-sm outline-none focus:border-brand"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />
        <div className="mt-4 rounded border border-line bg-panel p-3">
          <KeyValue label="Intencion" value={intent.intent} strong />
          <KeyValue label="Confianza" value={intent.confidence} />
        </div>
      </section>
    </div>
  );
}

function WhatsAppPage() {
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
      <section className="rounded border border-line bg-white p-4 shadow-soft">
        <h2 className="text-sm font-semibold">Cuenta Cloud API</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <Input label="Phone number ID" defaultValue="Configurar" />
          <Input label="Business account ID" defaultValue="Configurar" />
          <Input label="Verify token" defaultValue="change_me_verify_token" />
          <Input label="Estado" defaultValue="active" />
        </div>
        <button className="mt-4 inline-flex h-9 items-center gap-2 rounded bg-brand px-3 text-sm font-medium text-white">
          <Save className="h-4 w-4" />
          Guardar
        </button>
      </section>
      <InfoPanel title="Webhook" icon={MessageSquareText}>
        <KeyValue label="Verificacion" value="GET /webhooks/whatsapp" />
        <KeyValue label="Entrada" value="POST /webhooks/whatsapp" />
        <KeyValue label="Canal" value="whatsapp" strong />
      </InfoPanel>
    </div>
  );
}

function IntegrationsPage() {
  const integrations = [
    ["n8n", "Automatizaciones auxiliares", "pending"],
    ["Google Calendar", "Creacion de eventos", "pending"],
    ["SMTP", "Correos al equipo", "pending"],
    ["Webhook saliente", "Eventos por empresa", "active"],
  ];
  return (
    <section className="rounded border border-line bg-white shadow-soft">
      <SectionHeader title="Conectores" subtitle="No manejan estados criticos del SaaS" />
      <DataTable headers={["Tipo", "Uso", "Estado"]} rows={integrations} />
    </section>
  );
}

function SettingsPage() {
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
      <section className="rounded border border-line bg-white p-4 shadow-soft">
        <h2 className="text-sm font-semibold">Empresa</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <Input label="Nombre" defaultValue="SwaFlow" />
          <Input label="Estado" defaultValue="active" />
          <Input label="Rol actual" defaultValue="owner" />
          <Input label="API" defaultValue="http://127.0.0.1:8000" />
        </div>
      </section>
      <InfoPanel title="Base de datos" icon={CheckCircle2}>
        <KeyValue label="Motor" value="MariaDB 10.6" strong />
        <KeyValue label="Migracion" value="20260518_0001" />
        <KeyValue label="Tenant" value="company_id obligatorio" />
      </InfoPanel>
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
  action?: React.ReactNode;
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
  children: React.ReactNode;
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
  children: React.ReactNode;
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
    <div className="flex items-center justify-between gap-3">
      <span className="text-slate-600">{label}</span>
      <span className={strong ? "font-medium text-brand" : "font-medium"}>{value}</span>
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
