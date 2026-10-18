import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Plus, Download, Upload } from "lucide-react";

export default function InventoryPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Inventory Management
          </h1>
          <p className="text-sm text-[#64748b] mt-1">
            Global SKU tracking and multi-location physical inventory balances.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Upload className="w-4 h-4 mr-1.5" />
            Import CSV
          </Button>
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-1.5" />
            Export
          </Button>
          <Button variant="primary" size="sm">
            <Plus className="w-4 h-4 mr-1.5" />
            Add SKU
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Catalog Master & Stock Levels</CardTitle>
            <Badge variant="info">Architecture Schema Mounted</Badge>
          </div>
          <CardDescription>
            Row-level locking and append-only ledger transactions will be active upon Phase 4 execution.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-12 text-center text-sm text-[#64748b] border border-dashed border-[#cbd5e1] rounded-lg">
            <p className="font-medium text-[#0f172a]">No SKUs populated yet</p>
            <p className="text-xs text-[#94a3b8] mt-1">Use the Import CSV option or add items manually to begin tracking stock.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
