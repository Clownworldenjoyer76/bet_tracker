import { useEffect, useMemo } from "react";

type Props = {
  html: string;
  scripts: readonly string[];
};

function bodyOnly(html: string) {
  const match = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);

  return (match ? match[1] : html)
    .replace(/<div\s+id=["']nav-placeholder["']\s*><\/div>/gi, "")
    .replace(/<script\b[\s\S]*?<\/script>/gi, "");
}

export default function LegacyHtmlPage({ html, scripts }: Props) {
  const body = useMemo(() => bodyOnly(html), [html]);

  useEffect(() => {
    const mounted: HTMLScriptElement[] = [];
    let cancelled = false;

    const load = async () => {
      for (const src of scripts) {
        if (cancelled) return;

        await new Promise<void>((resolve, reject) => {
          const script = document.createElement("script");

          script.src = src;
          script.async = false;

          script.onload = () => resolve();
          script.onerror = () =>
            reject(new Error(`Failed loading ${src}`));

          document.body.appendChild(script);
          mounted.push(script);
        });
      }
    };

    load().catch(console.error);

    return () => {
      cancelled = true;
      mounted.forEach((script) => script.remove());
    };
  }, [scripts]);

  return (
    <div
      style={{ display: "contents" }}
      dangerouslySetInnerHTML={{ __html: body }}
    />
  );
}
