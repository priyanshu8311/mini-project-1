import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Package,
  TrendingUp,
  ShoppingCart,
  Database,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            System Overview & Foundation
          </h1>
          <p className="text-sm text-[#64748b] mt-1">
            Enterprise foundation initialized according to approved system architecture.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="success" icon={<CheckCircle2 className="w-3.5 h-3.5" />}>
            Foundation Ready
          </Badge>
        </div>
      </div>

      {/* KPI & Status Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>FastAPI Backend</CardTitle>
              <div className="w-2 h-2 rounded-full bg-[#16a34a]" />
            </div>
            <CardDescription>Port 8000 • Async Engine</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-sm font-semibold text-[#0f172a]">Modular Monolith</div>
            <p className="text-xs text-[#64748b] mt-1">Pydantic v2 • SQLAlchemy 2.0</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>PostgreSQL 15+</CardTitle>
              <Database className="w-4 h-4 text-[#2563eb]" />
            </div>
            <CardDescription>Ledger Pattern • RLS</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-sm font-semibold text-[#0f172a]">Asyncpg & Alembic</div>
            <p className="text-xs text-[#64748b] mt-1">Pessimistic Locking Ready</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Next.js Frontend</CardTitle>
              <div className="w-2 h-2 rounded-full bg-[#16a34a]" />
            </div>
            <CardDescription>App Router • Port 3000</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-sm font-semibold text-[#0f172a]">Tailwind CSS & Query</div>
            <p className="text-xs text-[#64748b] mt-1">8-point grid • Semantic Tokens</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Security & Auth</CardTitle>
              <Badge variant="info">JWT & RBAC</Badge>
            </div>
            <CardDescription>12-Factor App Config</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-sm font-semibold text-[#0f172a]">Tenant Isolation</div>
            <p className="text-xs text-[#64748b] mt-1">AES-256 External Secrets</p>
          </CardContent>
        </Card>
      </div>

      {/* Domain Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="hover:border-[#2563eb] transition-colors">
          <CardHeader>
            <div className="w-10 h-10 rounded-lg bg-[#eff6ff] flex items-center justify-center text-[#2563eb] mb-2">
              <Package className="w-5 h-5" />
            </div>
            <CardTitle>Inventory Operations</CardTitle>
            <CardDescription>
              Manage multi-location stock levels, track SKU attributes, and view immutable transaction ledgers.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/inventory">
              <Button variant="outline" size="sm" className="w-full justify-between">
                <span>View Inventory</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="hover:border-[#2563eb] transition-colors">
          <CardHeader>
            <div className="w-10 h-10 rounded-lg bg-[#f0fdf4] flex items-center justify-center text-[#16a34a] mb-2">
              <TrendingUp className="w-5 h-5" />
            </div>
            <CardTitle>Demand Forecasting</CardTitle>
            <CardDescription>
              XGBoost / Prophet machine learning pipelines forecasting SKU velocity and stockout risks.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/forecasting">
              <Button variant="outline" size="sm" className="w-full justify-between">
                <span>View Forecasts</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="hover:border-[#2563eb] transition-colors">
          <CardHeader>
            <div className="w-10 h-10 rounded-lg bg-[#fffbeb] flex items-center justify-center text-[#d97706] mb-2">
              <ShoppingCart className="w-5 h-5" />
            </div>
            <CardTitle>Replenishment & Orders</CardTitle>
            <CardDescription>
              Automated purchase order suggestions driven by safety stock thresholds and lead times.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/purchasing">
              <Button variant="outline" size="sm" className="w-full justify-between">
                <span>View Replenishment</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
