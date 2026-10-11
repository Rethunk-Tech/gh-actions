// Lint-clean, but gofmt would indent the function bodies, so only the format gate catches it.
package main

import "fmt"

func add(a int, b int) int {
return a + b
}

func main() {
fmt.Println(add(1, 2))
}
