import { Suspense } from "react";

import { RankingSection } from "@/components/ranking/ranking-section";
import { RankingSkeleton } from "@/components/ranking/ranking-skeleton";
import { SwimmerSearch } from "@/components/ranking/swimmer-search";

export default function HomePage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-10 px-4 py-10 sm:py-16">
      <section className="flex flex-col items-start gap-4 text-left">
        <span className="text-4xl" aria-hidden="true">
          🏊
        </span>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          FECNA Natación
        </h1>
        <p className="max-w-2xl text-muted-foreground">
          Rankings de natación de Colombia — datos públicos FECNA.
        </p>
        <div className="w-full max-w-md">
          <SwimmerSearch />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <Suspense fallback={<RankingSkeleton />}>
          <RankingSection />
        </Suspense>
      </section>
    </div>
  );
}
