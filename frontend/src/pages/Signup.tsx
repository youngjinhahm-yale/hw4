import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm: '',
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value })

  const mismatch = form.confirm.length > 0 && form.confirm !== form.password

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      const { confirm: _confirm, ...data } = form
      await signup(data)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the account.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="section auth">
      <h1 className="page-title">Create an account</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="auth-row">
          <label>
            First name
            <input
              autoComplete="given-name"
              value={form.first_name}
              onChange={set('first_name')}
              maxLength={50}
              required
            />
          </label>
          <label>
            Last name
            <input
              autoComplete="family-name"
              value={form.last_name}
              onChange={set('last_name')}
              maxLength={50}
              required
            />
          </label>
        </div>
        <label>
          Email
          <input
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={set('email')}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="new-password"
            value={form.password}
            onChange={set('password')}
            minLength={8}
            maxLength={128}
            required
          />
          <span className="hint">At least 8 characters.</span>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            autoComplete="new-password"
            value={form.confirm}
            onChange={set('confirm')}
            aria-invalid={mismatch}
            required
          />
          {mismatch && <span className="hint hint-error">Passwords do not match.</span>}
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button className="btn" type="submit" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </section>
  )
}
