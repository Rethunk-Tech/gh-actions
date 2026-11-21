// Package semverish is a fixture that changes the signature of a function the published
// module of the same path exports, which gorelease reports as an incompatible change.
package semverish

// Parse differs from the published signature on purpose.
func Parse(s string) (int, error) { return len(s), nil }
