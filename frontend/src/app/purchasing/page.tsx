import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Plus } from "lucide-react";

export default function PurchasingPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Replenishment & Purchase Orders
          </h1>
          <p className="text-sm text-[#64748b] mt-1">
            Automated reorder suggestions driven by lead time and predicted demand.
          </p>
        </div>
        <Button variant="primary" size="sm">
          <Plus className="w-4 h-4 mr-1.5" />
          Create Purchase Order
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Suggested Reorders</CardTitle>
            <Badge variant="info">Lead-Time Aware</Badge>
          </div>
          <CardDescription>
            Recommendations balance lead times, safety stocks, and active vendor constraints.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-12 text-center text-sm text-[#64748b] border border-dashed border-[#cbd5e1] rounded-lg">
            <p className="font-medium text-[#0f172a]">All items above reorder thresholds</p>
            <p className="text-xs text-[#94a3b8] mt-1">New purchase order recommendations will appear here automatically when stock dips.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
