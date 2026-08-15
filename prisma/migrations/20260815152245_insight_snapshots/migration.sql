-- CreateTable
CREATE TABLE "InsightSnapshot" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "period" TEXT NOT NULL,
    "volumeSent" INTEGER NOT NULL DEFAULT 0,
    "volumeReplies" INTEGER NOT NULL DEFAULT 0,
    "volumeLeads" INTEGER NOT NULL DEFAULT 0,
    "volumeCalls" INTEGER NOT NULL DEFAULT 0,
    "segmentStats" JSONB NOT NULL DEFAULT '[]',
    "classificationStats" JSONB NOT NULL DEFAULT '{}',
    "objectionClusters" JSONB NOT NULL DEFAULT '[]',
    "timingStats" JSONB NOT NULL DEFAULT '{}',
    "conclusions" JSONB NOT NULL DEFAULT '[]',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "InsightSnapshot_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "InsightSnapshot_tenantId_period_key" ON "InsightSnapshot"("tenantId", "period");

-- AddForeignKey
ALTER TABLE "InsightSnapshot" ADD CONSTRAINT "InsightSnapshot_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;
