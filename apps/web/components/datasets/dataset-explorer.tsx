"use client";

import { useEffect } from "react";
import { File, Folder, FolderOpen, Loader2 } from "lucide-react";

import { apiGet, type DatasetFileEntry } from "@/lib/api";
import { formatBytes, getErrorMessage } from "@/lib/format";
import { useFetchState } from "@/lib/hooks/use-fetch-state";
import { inferClientSurface, apiPathForSurface } from "@/lib/surface";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TableErrorState } from "@/components/shared/table-states";

type DatasetExplorerProps = {
  slug: string;
};

export function DatasetExplorer({ slug }: DatasetExplorerProps): React.JSX.Element {
  const [state, setState] = useFetchState<DatasetFileEntry[]>([]);

  useEffect(() => {
    const surface = inferClientSurface();
    const path = apiPathForSurface(surface, `/datasets/${slug}/files`);

    apiGet<DatasetFileEntry[]>(path)
      .then((files) => setState({ data: files, loading: false, error: null }))
      .catch((err) =>
        setState({ data: [], loading: false, error: getErrorMessage(err) }),
      );
  }, [slug, setState]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">File Explorer</CardTitle>
      </CardHeader>
      <CardContent>
        {state.loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        ) : state.error ? (
          <TableErrorState message={state.error} />
        ) : state.data.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <FolderOpen className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No files found in this dataset.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Size</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {state.data.map((entry) => (
                <TableRow key={entry.name}>
                  <TableCell className="flex items-center gap-2 font-medium">
                    {entry.type === "directory" ? (
                      <Folder className="size-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <File className="size-4 shrink-0 text-muted-foreground" />
                    )}
                    {entry.name}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {entry.type === "directory" ? "Folder" : "File"}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {formatBytes(entry.size)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
