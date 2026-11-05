import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.data.Value;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.instance.StdAttr;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.wiring.Pin;
import java.io.File;

/**
 * Verifica circuit/prueba_generador.circ simulandolo con Logisim (sin GUI).
 *
 * Uso: java -Djava.awt.headless=true --class-path "$env:LOGISIM_JAR" \
 *          tools/Verify.java circuit/prueba_generador.circ
 *
 * Conduce los pines A y B, propaga y lee los tuneles AND_OUT/OR_OUT/XOR_OUT/NOT_OUT.
 * Sale con codigo 1 si alguna fila de la tabla de verdad no coincide.
 */
class Verify {
  static Project project;
  static CircuitState state;

  static Component find(String kind, String label) {
    for (var c : state.getCircuit().getNonWires())
      if (c.getFactory().getName().equals(kind)
          && (label == null || label.equals(c.getAttributeSet().getValue(StdAttr.LABEL))))
        return c;
    throw new AssertionError("no se encontro " + kind + " " + label);
  }

  static void drive(String pin, boolean value) {
    var c = find("Pin", pin);
    ((Pin) c.getFactory()).driveInputPin(
        state.getInstanceState(c), value ? Value.TRUE : Value.FALSE);
    state.markComponentAsDirty(c);
  }

  static boolean read(String tunnel) {
    Value v = state.getValue(find("Tunnel", tunnel).getLocation());
    if (!v.isFullyDefined()) throw new AssertionError("senal indefinida en " + tunnel);
    return v == Value.TRUE;
  }

  static void settle() {
    state.getPropagator().propagate();
    if (state.getPropagator().isOscillating()) throw new AssertionError("oscilacion");
  }

  public static void main(String[] args) throws Exception {
    var file = new Loader(null).openLogisimFile(new File(args[0]));
    file.stopAutosaveThread(false);
    project = new Project(file);
    project.getSimulator().setAutoPropagation(false);
    project.getSimulator().setAutoTicking(false);
    project.getSimulator().shutDown();
    ((Thread) project.getSimulator().simThread).join(5000);

    state = CircuitState.createRootState(project, file.getMainCircuit(), Thread.currentThread());
    project.setCircuitState(state);
    settle();

    boolean todo = true;
    for (int a = 0; a < 2; a++) {
      for (int b = 0; b < 2; b++) {
        drive("A", a == 1);
        drive("B", b == 1);
        settle();
        boolean and = read("AND_OUT");
        boolean or = read("OR_OUT");
        boolean xor = read("XOR_OUT");
        boolean not = read("NOT_OUT");
        boolean esperado = and == (a == 1 && b == 1)
            && or == (a == 1 || b == 1)
            && xor == ((a == 1) ^ (b == 1))
            && not == (a == 0);
        System.out.printf("%s A=%d B=%d | AND=%b OR=%b XOR=%b NOT=%b%n",
            esperado ? "OK   " : "FALLO", a, b, and, or, xor, not);
        todo &= esperado;
      }
    }
    if (!todo) throw new AssertionError("tabla de verdad incorrecta");
    System.out.println("TODO OK");
  }
}
