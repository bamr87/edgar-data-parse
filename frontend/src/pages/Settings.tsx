/** Connection + admin tools: auth token, SEC contact email, theme, and the
 *  write actions (add company, bulk load, ingest) that require admin auth. */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { useApp } from '../lib/app-context'
import { useAddCompany } from '../lib/queries'
import { bulkFromEdgar, ingestSubmission } from '../lib/api'
import { PageHeader } from '../components/PageHeader'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Field,
  IconPlus,
  Segmented,
} from '../components/ui'

export function Settings() {
  const { token, email, theme, isAdmin, setToken, setEmail, setTheme } = useApp()
  const [tokenInput, setTokenInput] = useState(token)
  const [emailInput, setEmailInput] = useState(email)

  return (
    <div className="page">
      <PageHeader
        title="Settings"
        desc="Configure your connection to the backend and run admin data actions."
        badges={isAdmin ? <Badge tone="pos" dot>admin connected</Badge> : <Badge tone="warn" dot>read-only</Badge>}
      />

      <div className="grid grid-2">
        {/* Connection */}
        <Card>
          <CardHeader title="Connection" sub="Stored locally in your browser" />
          <div className="card-body col gap-4">
            <Field label="Admin API token" hint="DRF token for write/sync actions. Generate with: manage.py drf_create_token <user>">
              <div className="row gap-2">
                <input className="input" type="password" placeholder="paste token…" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} />
                <Button variant="primary" onClick={() => setToken(tokenInput)}>Save</Button>
              </div>
            </Field>
            <Field label="SEC contact email" hint="Sent as X-Sec-User-Agent-Email — SEC requires a contact for fair-access.">
              <div className="row gap-2">
                <input className="input" type="email" placeholder="you@example.com" value={emailInput} onChange={(e) => setEmailInput(e.target.value)} />
                <Button variant="primary" onClick={() => setEmail(emailInput)}>Save</Button>
              </div>
            </Field>
            <Field label="Theme">
              <Segmented
                value={theme}
                options={[{ value: 'system', label: 'System' }, { value: 'light', label: 'Light' }, { value: 'dark', label: 'Dark' }]}
                onChange={setTheme}
              />
            </Field>
          </div>
        </Card>

        {/* Add company */}
        <AddCompanyCard admin={isAdmin} />
      </div>

      {/* Admin bulk actions */}
      <div className="grid grid-2 mt-4">
        <BulkLoadCard admin={isAdmin} />
        <IngestCard admin={isAdmin} />
      </div>
    </div>
  )
}

function AddCompanyCard({ admin }: { admin: boolean }) {
  const navigate = useNavigate()
  const add = useAddCompany()
  const [ticker, setTicker] = useState('')
  const [cik, setCik] = useState('')

  return (
    <Card>
      <CardHeader title="Add a company from SEC" sub="Resolve & import by ticker or CIK" icon={<IconPlus width={16} height={16} />} />
      <div className="card-body col gap-3">
        <div className="row gap-2 wrap">
          <input className="input" placeholder="Ticker (e.g. AAPL)" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
          <input className="input" placeholder="or CIK" value={cik} onChange={(e) => setCik(e.target.value)} />
          <Button variant="primary" disabled={!admin || (!ticker && !cik)} loading={add.isPending} onClick={() => add.mutate({ ticker: ticker || undefined, cik: cik || undefined })}>
            Import
          </Button>
        </div>
        {!admin && <span className="caption warn">Requires an admin token (set it under Connection).</span>}
        {add.isError && <span className="caption neg">{(add.error as Error).message}</span>}
        {add.data && (
          <span className="caption pos">
            Imported {add.data.name}. <button className="link-btn" onClick={() => navigate(`/companies/${add.data!.id}`)}>Open profile →</button>
          </span>
        )}
      </div>
    </Card>
  )
}

function BulkLoadCard({ admin }: { admin: boolean }) {
  const bulk = useMutation({ mutationFn: () => bulkFromEdgar({ update_existing: false, refresh_sec_json: false }) })
  return (
    <Card>
      <CardHeader title="Bulk load company directory" sub="Upsert all companies from the SEC ticker file" />
      <div className="card-body col gap-3">
        <span className="caption">Loads the full SEC <code>company_tickers.json</code> directory into the warehouse. Rate-limited.</span>
        <Button disabled={!admin} loading={bulk.isPending} onClick={() => bulk.mutate()}>Run bulk load</Button>
        {!admin && <span className="caption warn">Requires an admin token.</span>}
        {bulk.isError && <span className="caption neg">{(bulk.error as Error).message}</span>}
        {bulk.data && <span className="caption pos">{bulk.data.message} (inserted {bulk.data.companies_inserted}, updated {bulk.data.companies_updated})</span>}
      </div>
    </Card>
  )
}

function IngestCard({ admin }: { admin: boolean }) {
  const [url, setUrl] = useState('')
  const [cik, setCik] = useState('')
  const ingest = useMutation({ mutationFn: () => ingestSubmission({ url, cik: cik || undefined }) })
  return (
    <Card>
      <CardHeader title="Ingest a full submission" sub="Decompose a .txt submission into searchable documents" />
      <div className="card-body col gap-3">
        <input className="input" placeholder="https://www.sec.gov/Archives/edgar/data/…/….txt" value={url} onChange={(e) => setUrl(e.target.value)} />
        <div className="row gap-2">
          <input className="input" placeholder="CIK" value={cik} onChange={(e) => setCik(e.target.value)} />
          <Button disabled={!admin || !url} loading={ingest.isPending} onClick={() => ingest.mutate()}>Ingest</Button>
        </div>
        {!admin && <span className="caption warn">Requires an admin token.</span>}
        {ingest.isError && <span className="caption neg">{(ingest.error as Error).message}</span>}
        {ingest.data && <span className="caption pos">Ingested {ingest.data.documents_ingested} documents (filing #{ingest.data.filing}).</span>}
      </div>
    </Card>
  )
}
