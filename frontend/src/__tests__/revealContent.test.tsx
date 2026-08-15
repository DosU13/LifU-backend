import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Reveal } from '../ui/Overlay'
import type { Prize } from '../ui/Overlay'
import type { GeneratedContent } from '../types'

const ICON = '/icons/receptacles/serenity_safe.png'

function content(overrides: Partial<GeneratedContent> = {}): GeneratedContent {
  return {
    kind: 'QUOTE',
    title: 'A thought',
    url: '',
    author: 'Marcus Aurelius',
    text: 'The obstacle is the way.',
    ...overrides,
  }
}

function show(prizeContent: GeneratedContent) {
  const prize: Prize = {
    image: ICON,
    title: 'Safe of Serenity',
    tier: 'gilded',
    content: prizeContent,
  }
  return render(<Reveal queue={[prize]} index={0} onAdvance={() => {}} onSkip={() => {}} />)
}

describe('Reveal — what a generated Pouch or Sack actually held', () => {
  it('prints a quote large and central, not tucked into the small note line', () => {
    show(content())

    expect(screen.getByText('The obstacle is the way.')).toBeInTheDocument()
    expect(screen.getByText('Marcus Aurelius')).toBeInTheDocument()
    expect(document.querySelector('.prize-quote')).toBeInTheDocument()
    // The oversized quotation mark is a decorative flourish, not literal
    // punctuation wrapping the sentence — kept out of the a11y tree.
    const mark = document.querySelector('.prize-quote-mark')
    expect(mark).toBeInTheDocument()
    expect(mark).toHaveAttribute('aria-hidden', 'true')
    // The rich content replaces the plain note — no matter what the caller
    // passed as a fallback, the passage wins.
    expect(document.querySelector('.prize-note')).not.toBeInTheDocument()
  })

  it('links a fact to its source', () => {
    show(
      content({
        kind: 'FACT',
        title: 'Did you know?',
        author: '',
        text: 'Honey never spoils.',
        url: 'https://example.com/honey',
      }),
    )

    const link = screen.getByRole('link', { name: /source/i })
    expect(link).toHaveAttribute('href', 'https://example.com/honey')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('shows art as an actual picture, plus a link to where it came from', () => {
    show(
      content({
        kind: 'ART',
        title: 'Nighthawks',
        author: 'Edward Hopper',
        url: 'https://example.com/nighthawks.jpg',
        text: 'https://example.com/nighthawks',
      }),
    )

    const img = screen.getByRole('img', { name: 'Nighthawks' })
    expect(img).toHaveAttribute('src', 'https://example.com/nighthawks.jpg')
    expect(screen.getByText('Nighthawks')).toBeInTheDocument()
    expect(screen.getByText('Edward Hopper')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /view source/i })
    expect(link).toHaveAttribute('href', 'https://example.com/nighthawks')
  })

  it('offers music as a listen-out link rather than trying to embed audio', () => {
    show(
      content({
        kind: 'MUSIC',
        title: 'Clair de Lune',
        author: 'Debussy',
        url: 'https://example.com/clair-de-lune',
        text: 'Suite bergamasque',
      }),
    )

    expect(screen.getByText('Clair de Lune')).toBeInTheDocument()
    expect(screen.getByText('Debussy')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /listen/i })
    expect(link).toHaveAttribute('href', 'https://example.com/clair-de-lune')
    // No audio element — an arbitrary stream URL is not safe to autoplay or trust.
    expect(document.querySelector('audio')).not.toBeInTheDocument()
  })

  it('gives a hand-written reward the same large passage treatment as a generated quote', () => {
    render(
      <Reveal
        queue={[
          { image: ICON, title: 'Safe of Serenity', tier: 'gilded', passage: 'Movie night, your pick.' },
        ]}
        index={0}
        onAdvance={() => {}}
        onSkip={() => {}}
      />,
    )

    expect(screen.getByText('Movie night, your pick.')).toBeInTheDocument()
    expect(document.querySelector('.prize-quote')).toBeInTheDocument()
    expect(document.querySelector('.prize-quote-mark')).toBeInTheDocument()
    // No author to cite — the passage stands alone, no attribution rule under it.
    expect(document.querySelector('.prize-attrib')).not.toBeInTheDocument()
  })

  it('falls back to the plain note when there is no generated content', () => {
    render(
      <Reveal
        queue={[{ image: ICON, title: 'Safe of Serenity', note: 'now find its key' }]}
        index={0}
        onAdvance={() => {}}
        onSkip={() => {}}
      />,
    )

    expect(screen.getByText('now find its key')).toBeInTheDocument()
    expect(document.querySelector('.prize-quote')).not.toBeInTheDocument()
  })
})
