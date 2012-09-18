from theano.tensor.io import send, recv, mpi_cmp, MPISend, MPISendWait
import theano
import subprocess
import os

def test_recv():
    x = recv((10,10), 'float64', 0, 11)
    assert x.dtype == 'float64'
    assert x.broadcastable == (False, False)

    recvnode = x.owner.inputs[0].owner
    assert recvnode.op.source == 0
    assert recvnode.op.tag    == 11

def test_send():
    x = theano.tensor.matrix('x')
    y = send(x, 1, 11)
    sendnode = y.owner.inputs[0].owner
    assert sendnode.op.dest == 1
    assert sendnode.op.tag  == 11

def test_can_make_function():
    x = recv((5,5), 'float32', 0, 11)
    y = x+1
    assert theano.function([], [y])

def test_mpi_roundtrip():
#    p = subprocess.Popen(executable="mpiexec",
#                         args = ("-np", "2",
#                                 "python",
#                                 "theano/tensor/tests/_test_mpi_roundtrip.py"),
#                         stdout=subprocess.PIPE)
#    assert p.stdout.read() == "True"
    result = os.popen("mpiexec -np 2 python "
                      "theano/tensor/tests/_test_mpi_roundtrip.py").read()
    assert result == "True"

def test_mpi_cmp():
    x = theano.tensor.matrix('x')
    y = send(x, 1, 11)
    z = x + x
    waitnode = y.owner
    sendnode = y.owner.inputs[0].owner
    addnode = z.owner
    assert mpi_cmp(sendnode, addnode) < 0 # send happens first
    assert mpi_cmp(waitnode, addnode) > 0 # wait happens last

def test_mpi_schedule():
    from theano.gof.graph import sort_schedule_fn
    scheduler = sort_schedule_fn(mpi_cmp)
    linker = theano.OpWiseCLinker(schedule=scheduler)
    mode = theano.Mode(linker=linker)

    x = theano.tensor.matrix('x')
    y = send(x, 1, 11)
    z = x + x
    waitnode = y.owner
    sendnode = y.owner.inputs[0].owner
    addnode = z.owner

    f = theano.function([x], [y, z], mode=mode)
    nodes = f.maker.linker.make_all()[-1]
    optypes = [MPISend, theano.tensor.Elemwise, MPISendWait]
    assert all(isinstance(node.op, optype)
            for node, optype in zip(nodes, optypes))

