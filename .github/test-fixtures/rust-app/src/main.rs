fn main() {
    let mut buf = itoa::Buffer::new();
    println!("{}", buf.format(42));
}

#[test]
fn formats_forty_two() {
    let mut buf = itoa::Buffer::new();
    assert_eq!(buf.format(42), "42");
}
