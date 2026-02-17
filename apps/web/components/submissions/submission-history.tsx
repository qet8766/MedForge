import { FileText } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface SubmissionHistoryProps {
  slug: string;
}

export function SubmissionHistory({ slug: _slug }: SubmissionHistoryProps): React.JSX.Element {
  return (
    <div className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16">#</TableHead>
            <TableHead>Score</TableHead>
            <TableHead>Submitted At</TableHead>
            <TableHead className="text-right">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell colSpan={4}>
              <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
                <div className="flex size-10 items-center justify-center rounded-full bg-muted">
                  <FileText className="size-5 text-muted-foreground" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium">No submissions yet</p>
                  <p className="text-xs text-muted-foreground">
                    Submit a CSV file to see your results here.
                  </p>
                </div>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  );
}
