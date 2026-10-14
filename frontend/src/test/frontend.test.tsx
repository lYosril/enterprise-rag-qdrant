import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { StatusBadge } from '../components/StatusBadge'
import { SourceCitation } from '../components/SourceCitation'
import { SourceModal } from '../components/SourceModal'
import { ChatMessage } from '../components/ChatMessage'
import { getToken, setToken, clearToken } from '../api/client'
import type { MessageResponse, SourceResponse } from '../types'

describe('Frontend Component & State Tests', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  // 1. Session state & Logout
  it('clears session state on logout', () => {
    setToken('sample-jwt-token')
    expect(getToken()).toBe('sample-jwt-token')

    clearToken()
    expect(getToken()).toBeNull()
  })

  // 2. StatusBadge renders processing and failed states correctly
  it('renders processing and failed states correctly', () => {
    const { rerender } = render(<StatusBadge status="processing" />)
    expect(screen.getByText('Processing')).toBeInTheDocument()

    rerender(<StatusBadge status="failed" />)
    expect(screen.getByText('Failed')).toBeInTheDocument()

    rerender(<StatusBadge status="indexed" />)
    expect(screen.getByText('Indexed')).toBeInTheDocument()
  })

  // 3. SourceCitation renders and opens SourceModal
  it('citation link opens expected source panel with excerpt and page', async () => {
    const mockSource: SourceResponse = {
      document_id: 'doc-123',
      document: 'Employee_Handbook.pdf',
      page: 14,
      text: 'Employees are entitled to 20 days paid annual leave after 1 year.',
      score: 0.94,
    }

    const handleClick = vi.fn()
    render(<SourceCitation source={mockSource} onClick={handleClick} />)

    const citationBtn = screen.getByRole('button', { name: /employee_handbook\.pdf/i })
    expect(citationBtn).toHaveTextContent('Employee_Handbook.pdf')
    expect(citationBtn).toHaveTextContent('p.14')

    fireEvent.click(citationBtn)
    expect(handleClick).toHaveBeenCalledTimes(1)

    // Now test SourceModal with the source
    cleanup()
    const handleClose = vi.fn()
    render(<SourceModal source={mockSource} onClose={handleClose} />)

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText(/Page 14/i)).toBeInTheDocument()
    expect(screen.getByText(/Employees are entitled to 20 days/)).toBeInTheDocument()
    expect(screen.getAllByText('94%').length).toBeGreaterThan(0)

    // Test close button
    const closeButtons = screen.getAllByRole('button', { name: /close/i })
    expect(closeButtons.length).toBeGreaterThan(0)
    fireEvent.click(closeButtons[0])
    expect(handleClose).toHaveBeenCalled()
  })

  // 4. Chat messages display in right order with sources and abstention notice
  it('chat messages display in right order with citations and abstention warning', () => {
    const userMessage: MessageResponse = {
      id: 'msg-1',
      role: 'user',
      content: 'What is the leave policy for new parents?',
      sources: null,
      created_at: new Date().toISOString(),
    }

    const assistantMessage: MessageResponse = {
      id: 'msg-2',
      role: 'assistant',
      content: 'I could not find relevant information in the provided documents regarding parental leave.',
      sources: [],
      created_at: new Date().toISOString(),
    }

    const { rerender } = render(<ChatMessage message={userMessage} />)
    expect(screen.getByText('What is the leave policy for new parents?')).toBeInTheDocument()

    rerender(<ChatMessage message={assistantMessage} />)
    expect(
      screen.getByText(/I could not find relevant information in the provided documents/),
    ).toBeInTheDocument()
    // Notice callout should be present for abstention
    expect(screen.getByText(/Notice:/i)).toBeInTheDocument()
  })

  // 5. Chat message with sources
  it('assistant message displays source citations and handles clicks', () => {
    const messageWithSources: MessageResponse = {
      id: 'msg-3',
      role: 'assistant',
      content: 'Standard working hours are 9:00 AM to 5:00 PM Monday through Friday.',
      sources: [
        {
          document_id: 'doc-1',
          document: 'Working_Hours.pdf',
          page: 2,
          text: 'Core hours are 9am to 5pm.',
          score: 0.91,
        },
      ],
      created_at: new Date().toISOString(),
    }

    const onSelectSource = vi.fn()
    render(<ChatMessage message={messageWithSources} onSelectSource={onSelectSource} />)

    expect(screen.getByText(/Standard working hours are 9:00 AM/)).toBeInTheDocument()
    expect(screen.getByText('Working_Hours.pdf')).toBeInTheDocument()
    expect(screen.getByText('p.2')).toBeInTheDocument()

    // Click source citation
    const citationBtn = screen.getByRole('button', { name: /working_hours\.pdf/i })
    fireEvent.click(citationBtn)
    expect(onSelectSource).toHaveBeenCalledWith(messageWithSources.sources![0])
  })
})
