import '@testing-library/jest-dom'
import { vi } from 'vitest'

Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockImplementation(() => Promise.resolve()),
  },
})
