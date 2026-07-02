import { BarChart3, ClipboardList } from 'lucide-react';

// Registry of skill expert modes. Each entry drives a route (App.jsx), a sidebar
// link (Sidebar.jsx), and a SkillPage. The `mode` value is sent to POST /ask and
// must match SKILL_REGISTRY in pi_backend/server.py.
// Theme classes are written out in full so Tailwind's scanner picks them up.
export const SKILLS = [
  {
    mode: 'reporting',
    path: '/reporting',
    navLabel: 'Reporting Expert',
    NavIcon: BarChart3,
    badge: 'Reporting Expert Mode',
    title: 'SQL Schema & Reporting Specialist',
    description:
      'This specialized interface uses Agility Reporting best practices. Ask about table grains, business key joins, and SQL patterns for the AgilitySQL schema.',
    engagementSource: 'reporting_expert',
    followUpSource: 'reporting_related_questions',
    exportName: 'reporting-session',
    prompts: [
      { label: 'How do I join item activity to orders?', icon: '📊' },
      { label: 'What is the grain of the so_detail table?', icon: '🎯' },
      { label: 'Give me a template for a sales by customer report', icon: '📑' },
      { label: 'Show business key joins for shipments', icon: '🔗' },
    ],
    rules: {
      title: '⚠️ Reporting Rules',
      items: [
        <>Never join on <code>prrowid</code>; always use business keys.</>,
        <>Be mindful of the grain (header vs detail).</>,
        <>Tables like <code>item_activity</code> need date filters for performance.</>,
      ],
    },
    theme: {
      badge: 'text-blue-600 dark:text-blue-400',
      hero: 'border-blue-500/20 bg-blue-500/5 dark:border-blue-500/30 dark:bg-blue-900/10',
      promptCard: 'hover:border-blue-500/40 hover:bg-blue-50/50 dark:hover:bg-blue-900/20',
      navIconActive: 'text-blue-400',
    },
  },
  {
    mode: 'sales_orders',
    path: '/sales-orders',
    navLabel: 'Sales Order Expert',
    NavIcon: ClipboardList,
    badge: 'Sales Order Expert Mode',
    title: 'Sales Order & Fulfillment Specialist',
    description:
      'Ask about entering and managing Agility sales orders — statuses, holds, pricing, shipping, and invoicing — answered from the Beisser sales order knowledge pack.',
    engagementSource: 'sales_order_expert',
    followUpSource: 'sales_orders_related_questions',
    exportName: 'sales-order-session',
    prompts: [
      { label: 'Walk me through the life of a sales order', icon: '🧭' },
      { label: 'Why would an order be blocked from shipping?', icon: '🚧' },
      { label: 'What can I still edit after picking starts?', icon: '✏️' },
      { label: 'How do orders connect to shipments and invoices?', icon: '🧾' },
    ],
    rules: {
      title: '📦 Sales Order Basics',
      items: [
        <>Orders flow quote → open order → pick → ship → invoice.</>,
        <>Holds (credit, review) block shipping until released.</>,
        <>Header sets customer, pricing, and tax; lines carry items and quantities.</>,
      ],
    },
    theme: {
      badge: 'text-orange-600 dark:text-orange-400',
      hero: 'border-orange-500/20 bg-orange-500/5 dark:border-orange-500/30 dark:bg-orange-900/10',
      promptCard: 'hover:border-orange-500/40 hover:bg-orange-50/50 dark:hover:bg-orange-900/20',
      navIconActive: 'text-orange-400',
    },
  },
];
