import { ExternalLink, Newspaper } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { formatDate } from "../lib/format";

type SourceItem = {
  rank: number;
  title: string;
  url: string;
  publisher: string | null;
  published_at: string | null;
  source_type: string | null;
};

type Props = {
  sources: SourceItem[];
};

export default function SourcesList({ sources }: Props) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Newspaper className="h-4 w-4 text-muted-foreground" aria-hidden />
            Sources & news
          </CardTitle>
          <CardDescription>External coverage and filings</CardDescription>
        </div>
        {sources.length > 0 && <Badge variant="muted">{sources.length}</Badge>}
      </CardHeader>

      <CardContent>
        {sources.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No sources available yet for this deal.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {sources.map((source) => (
              <li key={`${source.rank}-${source.url}`}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group flex items-start gap-3 rounded-xl border border-transparent p-3 transition-all hover:border-border hover:bg-muted/40"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border bg-muted/40 text-xs font-mono tabular-nums text-muted-foreground">
                    {String(source.rank).padStart(2, "0")}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <span className="line-clamp-2 text-sm font-medium leading-snug text-foreground transition-colors group-hover:text-accent">
                        {source.title}
                      </span>
                      <ExternalLink
                        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground/60 transition-colors group-hover:text-accent"
                        aria-hidden
                      />
                    </div>

                    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                      <span className="font-medium text-foreground/70">
                        {source.publisher ?? "Unknown"}
                      </span>
                      {source.published_at && (
                        <>
                          <span aria-hidden>·</span>
                          <time
                            dateTime={source.published_at}
                            className="tabular-nums"
                          >
                            {formatDate(source.published_at)}
                          </time>
                        </>
                      )}
                      {source.source_type && (
                        <Badge variant="muted" className="ml-auto">
                          {source.source_type}
                        </Badge>
                      )}
                    </div>
                  </div>
                </a>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
