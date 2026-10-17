      program p7calmsigma
c --- Test harness. SIGTY / SIGTZ are linked UNMODIFIED vendor units.
      include 'params.puf'
      include 'csigma.puf'
      include 'flags.puf'
      integer icase,ios
      real sy0,sz0,dt,dxkm,uavg,sv,sw,el,syhin,aytin,thftin
      real sy,sz,vty,vdy,vtz,vdz,dty,dtz,dx1,dx2
      open(unit=2,file='calm-idopt1-reference-list.txt',
     &     status='replace')
      do
         read(*,*,iostat=ios) icase,sy0,sz0,dt,dxkm,uavg,sv,sw,el,
     &        tyidr,tzidr,tzisdr,syhin,aytin,thftin
         if(ios.ne.0) exit
         idoptys=1
         idoptzs=1
         irus=0
         kstabs=4
         mhftszs=0
         uavgs=uavg
         tsigvs=sv
         tsigws=sw
         els=el
         syh=syhin
         ayt=aytin
         thfty=thftin
         dty=dt
         dtz=dt
         dx1=dxkm
         dx2=dxkm
         call sigty(sy0,dx1,dty,sy,vty,vdy)
         call sigtz(sz0,dx2,dtz,50.,sz,vtz,vdz)
         write(*,'(i8,6(1x,es18.10))')icase,sy,vty,vdy,sz,vtz,vdz
      enddo
      close(unit=2)
      end
