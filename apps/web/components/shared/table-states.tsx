export function TableErrorState({ message }: { message: string }): React.JSX.Element {
  return (
    <div className="py-8 text-center text-sm text-destructive">
      {message}
    </div>
  );
}

export function TableEmptyState({ message }: { message: string }): React.JSX.Element {
  return (
    <div className="py-8 text-center text-sm text-muted-foreground">
      {message}
    </div>
  );
}
