import { expect, test } from 'bun:test'
import { annotation, classify, type Report } from './audit.ts'

const advisory = (vulnerable_versions: string) => ({
  id: 1,
  url: 'https://github.com/advisories/GHSA-x',
  title: 't',
  severity: 'high',
  vulnerable_versions,
})

test('an advisory whose range excludes the latest release is fixable', () => {
  const report: Report = { lodash: [advisory('<4.17.21')] }
  const { fixable, unfixable } = classify(report, { lodash: '4.17.21' })
  expect(fixable.map((f) => f.pkg)).toEqual(['lodash'])
  expect(unfixable).toEqual([])
})

test('an advisory that still covers the latest release has no patch and only warns', () => {
  const report: Report = { oldlib: [advisory('>=1.0.0 <=2.3.0')] }
  const { fixable, unfixable } = classify(report, { oldlib: '2.3.0' })
  expect(fixable).toEqual([])
  expect(unfixable.map((f) => f.pkg)).toEqual(['oldlib'])
})

test('one package can split across both paths', () => {
  const report: Report = { p: [advisory('<1.0.1'), advisory('*')] }
  const { fixable, unfixable } = classify(report, { p: '1.0.1' })
  expect(fixable).toHaveLength(1)
  expect(unfixable).toHaveLength(1)
})

test('an unknown latest version fails closed', () => {
  const { fixable } = classify({ p: [advisory('*')] }, { p: undefined })
  expect(fixable).toHaveLength(1)
})

test('annotations encode newlines', () => {
  expect(annotation('warning', 'a\nb%')).toBe('::warning::a%0Ab%25')
})
