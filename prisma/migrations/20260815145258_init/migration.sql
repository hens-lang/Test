-- CreateEnum
CREATE TYPE "PlanType" AS ENUM ('CAMPAIGN', 'DATA_ONLY');

-- CreateEnum
CREATE TYPE "SubscriptionStatus" AS ENUM ('TRIAL', 'ACTIVE', 'PAUSED', 'CANCELED');

-- CreateEnum
CREATE TYPE "Role" AS ENUM ('ADMIN', 'MANAGER', 'CLIENT');

-- CreateEnum
CREATE TYPE "EmailStatus" AS ENUM ('UNVERIFIED', 'VALID', 'RISKY', 'INVALID', 'BOUNCED', 'UNSUBSCRIBED');

-- CreateEnum
CREATE TYPE "ContactSource" AS ENUM ('IMPORT', 'MANUAL', 'API', 'REFERRAL');

-- CreateEnum
CREATE TYPE "DomainStatus" AS ENUM ('PENDING', 'WARMING', 'ACTIVE', 'PAUSED', 'BLOCKED');

-- CreateEnum
CREATE TYPE "MailboxStatus" AS ENUM ('WARMING', 'ACTIVE', 'PAUSED', 'ERROR');

-- CreateEnum
CREATE TYPE "CampaignStatus" AS ENUM ('DRAFT', 'REVIEW', 'ACTIVE', 'PAUSED', 'COMPLETED');

-- CreateEnum
CREATE TYPE "EnrollmentStatus" AS ENUM ('PENDING_PERSONALIZATION', 'PENDING_APPROVAL', 'ACTIVE', 'REPLIED', 'BOUNCED', 'UNSUBSCRIBED', 'COMPLETED', 'STOPPED');

-- CreateEnum
CREATE TYPE "Variant" AS ENUM ('A', 'B');

-- CreateEnum
CREATE TYPE "ActivityType" AS ENUM ('EMAIL_QUEUED', 'EMAIL_SENT', 'EMAIL_OPENED', 'EMAIL_CLICKED', 'EMAIL_REPLIED', 'EMAIL_BOUNCED', 'EMAIL_UNSUBSCRIBED', 'LEAD_CREATED', 'REFERRAL_RECEIVED', 'NOTE', 'CALL_MADE', 'CALL_RESULT');

-- CreateEnum
CREATE TYPE "LeadStatus" AS ENUM ('NEW', 'QUALIFIED', 'MEETING_BOOKED', 'REJECTED');

-- CreateEnum
CREATE TYPE "ReferralStatus" AS ENUM ('SUGGESTED', 'APPROVED', 'REJECTED', 'CONTACT_CREATED');

-- CreateEnum
CREATE TYPE "ReplyDraftGeneratedBy" AS ENUM ('AI', 'RULE');

-- CreateEnum
CREATE TYPE "ReplyDraftStatus" AS ENUM ('PROPOSED', 'EDITED', 'SENT', 'DISCARDED');

-- CreateEnum
CREATE TYPE "TemplateStatScope" AS ENUM ('GLOBAL');

-- CreateEnum
CREATE TYPE "TemplateKind" AS ENUM ('SUBJECT', 'OPENER', 'BODY');

-- CreateEnum
CREATE TYPE "SuppressionReason" AS ENUM ('UNSUBSCRIBE', 'HARD_BOUNCE', 'MANUAL', 'COMPLAINT');

-- CreateEnum
CREATE TYPE "MessageDirection" AS ENUM ('OUT', 'IN');

-- CreateEnum
CREATE TYPE "ReplyClassification" AS ENUM ('POSITIVE', 'REFERRAL', 'NOT_NOW', 'NEGATIVE', 'OOO', 'UNSUBSCRIBE', 'BOUNCE', 'OTHER');

-- CreateTable
CREATE TABLE "Tenant" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "brandColor" TEXT,
    "logoUrl" TEXT,
    "industry" TEXT,
    "toneOfVoice" TEXT,
    "senderAddress" TEXT,
    "webhookUrl" TEXT,
    "shareTemplates" BOOLEAN NOT NULL DEFAULT true,
    "reportRecipients" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Tenant_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Plan" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "type" "PlanType" NOT NULL,
    "monthlyPriceCents" INTEGER NOT NULL,
    "setupFeeCents" INTEGER NOT NULL DEFAULT 0,
    "includedActiveProspects" INTEGER NOT NULL,
    "includedMailboxes" INTEGER NOT NULL,
    "features" JSONB NOT NULL DEFAULT '{}',
    "active" BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT "Plan_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Subscription" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "planId" TEXT NOT NULL,
    "status" "SubscriptionStatus" NOT NULL DEFAULT 'TRIAL',
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "canceledAt" TIMESTAMP(3),
    "priceOverrideCents" INTEGER,
    "notes" TEXT,

    CONSTRAINT "Subscription_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT,
    "email" TEXT NOT NULL,
    "passwordHash" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "role" "Role" NOT NULL,
    "lastLoginAt" TIMESTAMP(3),

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Company" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "domain" TEXT NOT NULL,
    "industry" TEXT,
    "size" TEXT,
    "city" TEXT,
    "country" TEXT NOT NULL DEFAULT 'NL',
    "linkedinUrl" TEXT,
    "websiteSummary" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Company_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Contact" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "companyId" TEXT NOT NULL,
    "firstName" TEXT NOT NULL,
    "lastName" TEXT NOT NULL,
    "title" TEXT,
    "email" TEXT NOT NULL,
    "emailStatus" "EmailStatus" NOT NULL DEFAULT 'UNVERIFIED',
    "emailCheckedAt" TIMESTAMP(3),
    "phone" TEXT,
    "linkedinUrl" TEXT,
    "source" "ContactSource" NOT NULL DEFAULT 'IMPORT',
    "customFields" JSONB NOT NULL DEFAULT '{}',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Contact_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SendingDomain" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "domain" TEXT NOT NULL,
    "dkimSelector" TEXT,
    "spfOk" BOOLEAN NOT NULL DEFAULT false,
    "dkimOk" BOOLEAN NOT NULL DEFAULT false,
    "dmarcOk" BOOLEAN NOT NULL DEFAULT false,
    "mxOk" BOOLEAN NOT NULL DEFAULT false,
    "lastCheckedAt" TIMESTAMP(3),
    "healthScore" INTEGER NOT NULL DEFAULT 0,
    "status" "DomainStatus" NOT NULL DEFAULT 'PENDING',
    "complaintCount" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "SendingDomain_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Mailbox" (
    "id" TEXT NOT NULL,
    "sendingDomainId" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "displayName" TEXT NOT NULL,
    "smtpHost" TEXT NOT NULL,
    "smtpPort" INTEGER NOT NULL DEFAULT 587,
    "smtpUser" TEXT NOT NULL,
    "smtpPassEncrypted" TEXT NOT NULL,
    "imapHost" TEXT NOT NULL,
    "imapPort" INTEGER NOT NULL DEFAULT 993,
    "imapUser" TEXT NOT NULL,
    "imapPassEncrypted" TEXT NOT NULL,
    "dailyCap" INTEGER NOT NULL DEFAULT 10,
    "maxDailyCap" INTEGER NOT NULL DEFAULT 50,
    "warmupStartedAt" TIMESTAMP(3),
    "warmupDay" INTEGER NOT NULL DEFAULT 0,
    "status" "MailboxStatus" NOT NULL DEFAULT 'WARMING',
    "sentToday" INTEGER NOT NULL DEFAULT 0,
    "bouncedToday" INTEGER NOT NULL DEFAULT 0,
    "consecutiveSmtpErrors" INTEGER NOT NULL DEFAULT 0,
    "lastResetAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "lastImapUid" INTEGER NOT NULL DEFAULT 0,
    "lastError" TEXT,

    CONSTRAINT "Mailbox_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Campaign" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "status" "CampaignStatus" NOT NULL DEFAULT 'DRAFT',
    "timezone" TEXT NOT NULL DEFAULT 'Europe/Amsterdam',
    "sendWindowStart" TEXT NOT NULL DEFAULT '08:30',
    "sendWindowEnd" TEXT NOT NULL DEFAULT '17:00',
    "sendDays" TEXT NOT NULL DEFAULT '1,2,3,4,5',
    "dailyCampaignCap" INTEGER,
    "requiresApproval" BOOLEAN NOT NULL DEFAULT true,
    "trackingEnabled" BOOLEAN NOT NULL DEFAULT true,
    "shareTemplates" BOOLEAN NOT NULL DEFAULT true,
    "audienceFilter" JSONB NOT NULL DEFAULT '{}',
    "proposition" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Campaign_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SequenceStep" (
    "id" TEXT NOT NULL,
    "campaignId" TEXT NOT NULL,
    "order" INTEGER NOT NULL,
    "waitDays" INTEGER NOT NULL DEFAULT 0,
    "subjectA" TEXT NOT NULL,
    "bodyA" TEXT NOT NULL,
    "subjectB" TEXT,
    "bodyB" TEXT,
    "abSplit" INTEGER NOT NULL DEFAULT 50,

    CONSTRAINT "SequenceStep_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Enrollment" (
    "id" TEXT NOT NULL,
    "campaignId" TEXT NOT NULL,
    "contactId" TEXT NOT NULL,
    "mailboxId" TEXT NOT NULL,
    "currentStep" INTEGER NOT NULL DEFAULT 0,
    "status" "EnrollmentStatus" NOT NULL DEFAULT 'PENDING_PERSONALIZATION',
    "variant" "Variant" NOT NULL DEFAULT 'A',
    "personalizedOpener" TEXT,
    "openerApprovedBy" TEXT,
    "nextSendAt" TIMESTAMP(3),
    "oooPausedUntil" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Enrollment_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Activity" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "contactId" TEXT NOT NULL,
    "campaignId" TEXT,
    "enrollmentId" TEXT,
    "type" "ActivityType" NOT NULL,
    "meta" JSONB NOT NULL DEFAULT '{}',
    "occurredAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Activity_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Lead" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "contactId" TEXT NOT NULL,
    "campaignId" TEXT NOT NULL,
    "status" "LeadStatus" NOT NULL DEFAULT 'NEW',
    "replySnippet" TEXT NOT NULL,
    "viaReferral" BOOLEAN NOT NULL DEFAULT false,
    "assignedTo" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Lead_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Referral" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "sourceContactId" TEXT NOT NULL,
    "sourceMessageId" TEXT NOT NULL,
    "suggestedName" TEXT,
    "suggestedEmail" TEXT,
    "suggestedTitle" TEXT,
    "suggestedCompany" TEXT,
    "rawSnippet" TEXT NOT NULL,
    "status" "ReferralStatus" NOT NULL DEFAULT 'SUGGESTED',
    "createdContactId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Referral_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ReplyDraft" (
    "id" TEXT NOT NULL,
    "messageId" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "draftSubject" TEXT NOT NULL,
    "draftBody" TEXT NOT NULL,
    "generatedBy" "ReplyDraftGeneratedBy" NOT NULL,
    "status" "ReplyDraftStatus" NOT NULL DEFAULT 'PROPOSED',
    "finalBody" TEXT,
    "sentMessageId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ReplyDraft_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "TemplateStat" (
    "id" TEXT NOT NULL,
    "scope" "TemplateStatScope" NOT NULL DEFAULT 'GLOBAL',
    "industry" TEXT NOT NULL,
    "kind" "TemplateKind" NOT NULL,
    "textHash" TEXT NOT NULL,
    "textSample" TEXT NOT NULL,
    "sentCount" INTEGER NOT NULL DEFAULT 0,
    "replyCount" INTEGER NOT NULL DEFAULT 0,
    "positiveCount" INTEGER NOT NULL DEFAULT 0,
    "lastUsedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "TemplateStat_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "DataHealthRun" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "ranAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "contactsChecked" INTEGER NOT NULL DEFAULT 0,
    "newInvalid" INTEGER NOT NULL DEFAULT 0,
    "newRisky" INTEGER NOT NULL DEFAULT 0,
    "bouncesRemoved" INTEGER NOT NULL DEFAULT 0,
    "suppressed" INTEGER NOT NULL DEFAULT 0,
    "enriched" INTEGER NOT NULL DEFAULT 0,
    "reportJson" JSONB NOT NULL DEFAULT '{}',

    CONSTRAINT "DataHealthRun_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Suppression" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT,
    "email" TEXT NOT NULL,
    "reason" "SuppressionReason" NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Suppression_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Message" (
    "id" TEXT NOT NULL,
    "enrollmentId" TEXT,
    "tenantId" TEXT NOT NULL,
    "direction" "MessageDirection" NOT NULL,
    "messageId" TEXT NOT NULL,
    "inReplyTo" TEXT,
    "subject" TEXT NOT NULL,
    "body" TEXT NOT NULL,
    "classifiedAs" "ReplyClassification",
    "classificationConfirmed" BOOLEAN NOT NULL DEFAULT false,
    "fromEmail" TEXT,
    "toEmail" TEXT,
    "mailboxEmail" TEXT,
    "sentAt" TIMESTAMP(3),
    "receivedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Message_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AuditLog" (
    "id" TEXT NOT NULL,
    "userId" TEXT,
    "action" TEXT NOT NULL,
    "entity" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "meta" JSONB NOT NULL DEFAULT '{}',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "AuditLog_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Tenant_slug_key" ON "Tenant"("slug");

-- CreateIndex
CREATE INDEX "Subscription_tenantId_idx" ON "Subscription"("tenantId");

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE INDEX "Company_tenantId_idx" ON "Company"("tenantId");

-- CreateIndex
CREATE UNIQUE INDEX "Company_tenantId_domain_key" ON "Company"("tenantId", "domain");

-- CreateIndex
CREATE INDEX "Contact_tenantId_emailStatus_idx" ON "Contact"("tenantId", "emailStatus");

-- CreateIndex
CREATE UNIQUE INDEX "Contact_tenantId_email_key" ON "Contact"("tenantId", "email");

-- CreateIndex
CREATE UNIQUE INDEX "SendingDomain_tenantId_domain_key" ON "SendingDomain"("tenantId", "domain");

-- CreateIndex
CREATE UNIQUE INDEX "Mailbox_email_key" ON "Mailbox"("email");

-- CreateIndex
CREATE INDEX "Campaign_tenantId_idx" ON "Campaign"("tenantId");

-- CreateIndex
CREATE UNIQUE INDEX "SequenceStep_campaignId_order_key" ON "SequenceStep"("campaignId", "order");

-- CreateIndex
CREATE INDEX "Enrollment_status_nextSendAt_idx" ON "Enrollment"("status", "nextSendAt");

-- CreateIndex
CREATE UNIQUE INDEX "Enrollment_campaignId_contactId_key" ON "Enrollment"("campaignId", "contactId");

-- CreateIndex
CREATE INDEX "Activity_tenantId_occurredAt_idx" ON "Activity"("tenantId", "occurredAt");

-- CreateIndex
CREATE INDEX "Activity_contactId_idx" ON "Activity"("contactId");

-- CreateIndex
CREATE INDEX "Lead_tenantId_createdAt_idx" ON "Lead"("tenantId", "createdAt");

-- CreateIndex
CREATE INDEX "Referral_tenantId_status_idx" ON "Referral"("tenantId", "status");

-- CreateIndex
CREATE INDEX "ReplyDraft_tenantId_status_idx" ON "ReplyDraft"("tenantId", "status");

-- CreateIndex
CREATE UNIQUE INDEX "TemplateStat_industry_kind_textHash_key" ON "TemplateStat"("industry", "kind", "textHash");

-- CreateIndex
CREATE INDEX "DataHealthRun_tenantId_ranAt_idx" ON "DataHealthRun"("tenantId", "ranAt");

-- CreateIndex
CREATE INDEX "Suppression_email_idx" ON "Suppression"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Suppression_tenantId_email_key" ON "Suppression"("tenantId", "email");

-- CreateIndex
CREATE INDEX "Message_tenantId_direction_idx" ON "Message"("tenantId", "direction");

-- CreateIndex
CREATE INDEX "Message_messageId_idx" ON "Message"("messageId");

-- CreateIndex
CREATE INDEX "AuditLog_entity_entityId_idx" ON "AuditLog"("entity", "entityId");

-- AddForeignKey
ALTER TABLE "Subscription" ADD CONSTRAINT "Subscription_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Subscription" ADD CONSTRAINT "Subscription_planId_fkey" FOREIGN KEY ("planId") REFERENCES "Plan"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "User" ADD CONSTRAINT "User_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Company" ADD CONSTRAINT "Company_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Contact" ADD CONSTRAINT "Contact_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Contact" ADD CONSTRAINT "Contact_companyId_fkey" FOREIGN KEY ("companyId") REFERENCES "Company"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SendingDomain" ADD CONSTRAINT "SendingDomain_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Mailbox" ADD CONSTRAINT "Mailbox_sendingDomainId_fkey" FOREIGN KEY ("sendingDomainId") REFERENCES "SendingDomain"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Campaign" ADD CONSTRAINT "Campaign_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SequenceStep" ADD CONSTRAINT "SequenceStep_campaignId_fkey" FOREIGN KEY ("campaignId") REFERENCES "Campaign"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Enrollment" ADD CONSTRAINT "Enrollment_campaignId_fkey" FOREIGN KEY ("campaignId") REFERENCES "Campaign"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Enrollment" ADD CONSTRAINT "Enrollment_contactId_fkey" FOREIGN KEY ("contactId") REFERENCES "Contact"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Enrollment" ADD CONSTRAINT "Enrollment_mailboxId_fkey" FOREIGN KEY ("mailboxId") REFERENCES "Mailbox"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Activity" ADD CONSTRAINT "Activity_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Activity" ADD CONSTRAINT "Activity_contactId_fkey" FOREIGN KEY ("contactId") REFERENCES "Contact"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Activity" ADD CONSTRAINT "Activity_campaignId_fkey" FOREIGN KEY ("campaignId") REFERENCES "Campaign"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Activity" ADD CONSTRAINT "Activity_enrollmentId_fkey" FOREIGN KEY ("enrollmentId") REFERENCES "Enrollment"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Lead" ADD CONSTRAINT "Lead_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Lead" ADD CONSTRAINT "Lead_contactId_fkey" FOREIGN KEY ("contactId") REFERENCES "Contact"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Lead" ADD CONSTRAINT "Lead_campaignId_fkey" FOREIGN KEY ("campaignId") REFERENCES "Campaign"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Referral" ADD CONSTRAINT "Referral_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ReplyDraft" ADD CONSTRAINT "ReplyDraft_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ReplyDraft" ADD CONSTRAINT "ReplyDraft_messageId_fkey" FOREIGN KEY ("messageId") REFERENCES "Message"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "DataHealthRun" ADD CONSTRAINT "DataHealthRun_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Suppression" ADD CONSTRAINT "Suppression_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Message" ADD CONSTRAINT "Message_tenantId_fkey" FOREIGN KEY ("tenantId") REFERENCES "Tenant"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Message" ADD CONSTRAINT "Message_enrollmentId_fkey" FOREIGN KEY ("enrollmentId") REFERENCES "Enrollment"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AuditLog" ADD CONSTRAINT "AuditLog_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;
