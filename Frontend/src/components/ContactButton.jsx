import { useMemo, useState } from 'react'
import { submitContactReport } from '../utils/dataLayer'

const REPORT_TYPES = [
  { value: 'bug', label: 'Bug reporting' },
  { value: 'missing_information', label: 'Missing information' },
  { value: 'incorrect_information', label: 'Incorrect information' },
  { value: 'general_contact', label: 'General contact' },
]

const TOPICS = [
  { value: 'pokemon', label: 'Pokemon' },
  { value: 'trainer', label: 'Trainer' },
  { value: 'other', label: 'Other' },
]

function ContactButton({ context = {}, className = 'page-action-button', buttonLabel = 'Contact' }) {
  const [open, setOpen] = useState(false)
  const [reportType, setReportType] = useState('bug')
  const [topic, setTopic] = useState('pokemon')
  const [title, setTitle] = useState('')
  const [details, setDetails] = useState('')
  const [reproductionSteps, setReproductionSteps] = useState('')
  const [status, setStatus] = useState({ state: 'idle', message: '' })

  const needsTopic = reportType === 'missing_information' || reportType === 'incorrect_information'
  const detailLabel = useMemo(() => {
    if (reportType === 'bug') return 'What happened?'
    if (reportType === 'missing_information') return 'What information is missing?'
    if (reportType === 'incorrect_information') return 'What information is incorrect?'
    return 'Message'
  }, [reportType])

  const handleClose = () => {
    setOpen(false)
    setStatus({ state: 'idle', message: '' })
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setStatus({ state: 'submitting', message: '' })

    const payload = {
      report_type: reportType,
      topic: needsTopic ? topic : null,
      title,
      details,
      reproduction_steps: reportType === 'bug' ? reproductionSteps : '',
      page_url: window.location.href,
      user_agent: navigator.userAgent,
      run_id: context.runId || null,
      attempt_number: context.attemptId || null,
      game_id: context.gameId || null,
      version_group_id: context.versionGroupId || null,
      run_name: context.runName || null,
      game_name: context.gameName || null,
    }

    try {
      const result = await submitContactReport(payload)
      if (!result?.success) {
        throw new Error(result?.error || 'Unable to send report.')
      }
      setStatus({ state: 'sent', message: 'Submitted. Thank you.' })
      setTitle('')
      setDetails('')
      setReproductionSteps('')
    } catch (error) {
      setStatus({ state: 'error', message: error.message || 'Unable to send report.' })
    }
  }

  return (
    <>
      <button type="button" className={className} onClick={() => setOpen(true)}>
        {buttonLabel}
      </button>

      {open && (
        <div className="contact-panel__backdrop" onClick={handleClose}>
          <form className="contact-panel" onSubmit={handleSubmit} onClick={event => event.stopPropagation()}>
            <div className="contact-panel__header">
              <div>
                <h2 className="contact-panel__title">Contact</h2>
                <p className="contact-panel__subtitle">Send a report with the current page context attached.</p>
              </div>
              <button type="button" className="contact-panel__close" onClick={handleClose}>Close</button>
            </div>

            <label className="contact-panel__field">
              <span>Reason</span>
              <select value={reportType} onChange={event => setReportType(event.target.value)}>
                {REPORT_TYPES.map(option => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>

            {needsTopic && (
              <label className="contact-panel__field">
                <span>Topic</span>
                <select value={topic} onChange={event => setTopic(event.target.value)}>
                  {TOPICS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
            )}

            <label className="contact-panel__field">
              <span>Short title</span>
              <input value={title} onChange={event => setTitle(event.target.value)} placeholder="Optional summary" maxLength={160} />
            </label>

            <label className="contact-panel__field">
              <span>{detailLabel}</span>
              <textarea value={details} onChange={event => setDetails(event.target.value)} required rows={5} />
            </label>

            {reportType === 'bug' && (
              <label className="contact-panel__field">
                <span>How can I recreate it?</span>
                <textarea value={reproductionSteps} onChange={event => setReproductionSteps(event.target.value)} rows={4} />
              </label>
            )}

            {status.message && (
              <div className={`contact-panel__status contact-panel__status--${status.state}`}>
                {status.message}
              </div>
            )}

            <div className="contact-panel__actions">
              <button type="button" className="page-action-button" onClick={handleClose}>Cancel</button>
              <button type="submit" className="page-action-button page-action-button--success" disabled={status.state === 'submitting'}>
                {status.state === 'submitting' ? 'Sending...' : 'Submit'}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  )
}

export default ContactButton
