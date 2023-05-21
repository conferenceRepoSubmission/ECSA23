class SuperclassExample {
	// Uses
	private ComposedClass c;

	// Owns, Returns
	public ComposedClass get()
	{
		return c;
	}

	// Owns, Returns
	public String get_c_s()
	{
		int a = 0;
		float b = 3;
		String x2, x3;
		// Variable, Calls
		String x = c.get_s();
		x2 = " s2 ";
		x3 = " s3 ";
		return x + x2 + x3;
	}
}
