c-----------------------------------------------------------------------
      program p7d_sigma_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7D FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it only drives the UNMODIFIED vendor units extracted by
c     reference/sigma_source_anchor.py (BLOCK DATA, SIGSET, SIGTY, SIGTZ,
c     XVY, XVZ, WARN) so the P7D C++ dispersion coefficients can be
c     compared against the original algorithm and tables.
c
c --- Read one case per line from stdin (list directed):
c       icase idopty idoptz iru kst mhftsz uavg sigy0 sigz0 dxkm dt zht
c             sytdep avefac yz0fac az0fac bz0trm
c     and write one result per line to stdout:
c       icase sigy virty virdy sigz virtz virdz thfty
c
c --- Column meanings follow the vendor routines: IDOPTY/IDOPTZ = dispersion
c     option (MDISP) for sigma-y and sigma-z, IRU = 0 rural / 1 urban,
c     KST = PGT stability class, UA VG = mean transport speed (m/s),
c     SIGY0/SIGZ0 = sigma at start of step (m), DXKM = travel distance
c     increment (km), DT = travel time increment (s), ZHT = puff height (m),
c     SYTDEP = sigma-y at Heffter transition (m), AVEFAC = averaging time
c     factor applied to the rural PG sigma-y curve, YZ0FAC/AZ0FAC/BZ0TRM =
c     gridded roughness adjustment factors (1.0/1.0/-1000.0 = none).
c
c --- AVET and PGTIME are kept equal so the vendor SIGSET stays silent, and the
c     averaging factor is supplied directly through /CSIGMA/ AVEFAC afterwards.
c
c --- Notes kept deliberately identical to SETCSIG: the stability class is
c     conditioned to 1-6, the Heffter transition virtual time THFTY is
c     obtained by calling SIGTY with SIGY0 = SYH and zero increments, and
c     TAULY is not called (MTAULY=0 in the selected case; SIGTY only uses
c     TYIDR for IDOPTYS 1,2 and 5).
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'csigma.puf'
      include 'dispdat.puf'
      include 'flags.puf'
      include 'gridnest.puf'
      include 'comparm.puf'
c
      integer icase,idopty,idoptz,iru,kst,mhftsz,ios
      real uavg,sigy0,sigz0,dxkm,dt,zht,sytdep,avefacin
      real yrfac,zafac,zbtrm
      real sigy,virty,virdy,sigz,virtz,virdz,thfty,dum,dhfty
      real dxkmy,dty,dxkmz,dtz
c
      data zero/0.0/
c
c --- Vendor list file unit (IO6 = 2) is redirected so diagnostics from the
c     extracted vendor code never mix with the stdout result stream.
      open(unit=2,file='sigma-oracle-list.txt',status='replace')
c
c --- Engine roughness adjustment is exercised through explicit factors; the
c     vendor SIGSET is called with MROUGH=0 and the cell factors are then
c     overwritten, exactly the values SIGTY/SIGTZ read from /CSIGMA/.
      mrough=0
c
      do
         read(*,*,iostat=ios) icase,idopty,idoptz,iru,kst,mhftsz,uavg,
     &        sigy0,sigz0,dxkm,dt,zht,sytdep,avefacin,yrfac,zafac,zbtrm
         if(ios.ne.0) exit
c
c ---    Per-run setup: PG/MESOPUFF tables, sigma-z junctions, SYH
         avet=pgtime
         call sigset
         avefac=avefacin
         avefaci=1.0/avefacin
c
c ---    Roughness factor for the current cell
         ixcell=1
         iycell=1
         mdcell=1
         yz0fac(1,1,1)=yrfac
         az0fac(1,1,1)=zafac
         bz0trm(1,1,1)=zbtrm
c
c ---    Per-puff state (SETCSIG equivalent)
         idoptys=idopty
         idoptzs=idoptz
         irus=iru
         uavgs=uavg
         kstabs=kst
         els=zero
         bvfs=zero
         mhftszs=mhftsz
         tsigvs=zero
         tsigws=zero
         symins=zero
         szmins=zero
         if(kstabs.gt.6) kstabs=6
         call sigty(syh,zero,zero,dum,thfty,dhfty)
c
c ---    Sigma-y and sigma-z keep independent increment copies, as the
c        vendor SIGMA entry point calls only one of them per invocation.
         dxkmy=dxkm
         dty=dt
         dxkmz=dxkm
         dtz=dt
         call sigty(sigy0,dxkmy,dty,sigy,virty,virdy)
         call sigtz(sigz0,dxkmz,dtz,zht,sigz,virtz,virdz)
         write(*,'(i8,7(1x,es18.10))') icase,sigy,virty,virdy,sigz,
     &        virtz,virdz,thfty
      enddo
      close(unit=2)
      end
