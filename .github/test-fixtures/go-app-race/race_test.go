package main

import (
	"sync"
	"testing"
)

// Two goroutines write one variable with no synchronization. The test passes without -race
// and fails under it, so only the race gate can catch it.
func TestRace(t *testing.T) {
	var n int
	var wg sync.WaitGroup
	for range 2 {
		wg.Go(func() { n++ })
	}
	wg.Wait()
	_ = n
}
