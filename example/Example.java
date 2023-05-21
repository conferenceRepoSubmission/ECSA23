// Import
import java.util.ArrayList;

// Extends, Implements
public class Example extends SuperclassExample implements InterfaceExample {
	// Owns
	public static void main(String[] args)
	{
		// Calls
		System.out.println("Hello world");
		// Calls
		prova();
		// Calls
		System.out.println("Hello world 2");
	}

	// Owns
	public static int prova()
	{
		// Variable
		String[] ss = {"ciao"};

		// Variable
		ArrayList<String> a1 = new ArrayList<>();
		// Calls
		a1.add("ciao");
		// Calls
		System.out.println(a1.get(0));
		// Calls
		System.out.println(ss[0]);

		return 1;
	}

	public void method(int a, int b)
	{
		// Calls
		System.out.println(a + b);
	}
}

